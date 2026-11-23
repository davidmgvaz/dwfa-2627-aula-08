"""ViewSets · sem N+1 nos endpoints de lista · no N+1 on list endpoints."""

from celery.result import AsyncResult
from django.core.cache import cache
from django.db.models import F, Prefetch, Sum
from django.urls import reverse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .cache import catalogue_version
from .filters import OrderFilter, ProductFilter
from .models import LINE_TOTAL, Category, Customer, Order, OrderItem, Payment, Product
from .permissions import IsGestor, IsGestorOrReadOnly, IsOwnerOrGestor, is_gestor
from .serializers import (
    CategorySerializer,
    CustomerSerializer,
    GestorOrderSerializer,
    OrderItemSerializer,
    OrderSerializer,
    PaymentSerializer,
    ProductSerializer,
    TaskAcceptedSerializer,
    TaskStatusSerializer,
)
from .services import Conflict, cancel_order, pay_order
from .tasks import export_orders_report


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]  # catálogo público, de propósito · public catalogue, on purpose
    search_fields = ["name"]
    ordering_fields = ["name"]

    def list(self, request, *args, **kwargs):
        # Ficha 05 — cache de resposta: pública e igual para toda a gente, logo segura de cachear
        # a chave leva a versão do catálogo (bump por sinal) e o URL completo (página, pesquisa).
        # NUNCA fazer isto a /orders/: a resposta depende de quem pergunta.
        # Ficha 05 — response cache: public and identical for everyone, hence safe to cache; the key
        # embeds the catalogue version (bumped by a signal) and the full URL (page, search).
        # NEVER do this to /orders/: the response depends on who is asking.
        key = f"categories:v{catalogue_version()}:{request.get_full_path()}"
        data = cache.get(key)
        hit = data is not None
        if not hit:
            data = super().list(request, *args, **kwargs).data
            cache.set(key, data, timeout=300)
        return Response(data, headers={"X-Cache": "HIT" if hit else "MISS"})


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category")
    serializer_class = ProductSerializer
    # leitura pública, escrita só para gestores · public reads, writes for managers only
    permission_classes = [IsGestorOrReadOnly]
    filterset_class = ProductFilter
    search_fields = ["name", "sku"]
    ordering_fields = ["price", "name", "created_at"]
    ordering = ["name"]


class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Customer.objects.select_related("user")
    serializer_class = CustomerSerializer
    permission_classes = [IsGestor]
    search_fields = ["user__username", "user__email"]


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.none()  # só para o drf-spectacular; o real está em get_queryset
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrGestor]
    filterset_class = OrderFilter
    ordering_fields = ["created_at", "total"]
    ordering = [
        "-created_at"
    ]  # explícito: annotate() perde o Meta.ordering · annotate() drops Meta.ordering
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        items = OrderItem.objects.select_related("product").annotate(
            line_total=F("quantity") * F("unit_price")
        )
        qs = (
            Order.objects.select_related("customer__user")
            .prefetch_related(Prefetch("items", queryset=items))
            .annotate(total=Sum(LINE_TOTAL))
        )
        # camada 1: o cliente só vê as suas; uma alheia é 404, não 403
        # layer 1: a customer only sees their own; someone else's is a 404, not a 403
        if is_gestor(self.request.user):
            return qs
        return qs.filter(customer__user=self.request.user)

    def get_serializer_class(self):
        if is_gestor(self.request.user):
            return GestorOrderSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        # o dono vem do pedido, nunca do corpo · the owner comes from the request, never the body
        customer, _ = Customer.objects.get_or_create(user=self.request.user)
        serializer.save(customer=customer)

    @extend_schema(
        request=None,
        responses={200: OrderSerializer, 409: OpenApiResponse(description="Order is not pending")},
    )
    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        pay_order(self.get_object())
        return Response(self.get_serializer(self.get_object()).data)

    @extend_schema(
        request=None,
        responses={200: OrderSerializer, 409: OpenApiResponse(description="Order is not pending")},
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        cancel_order(self.get_object())
        return Response(self.get_serializer(self.get_object()).data)


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.none()  # schema only · the real one is get_queryset
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["order", "product"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = OrderItem.objects.select_related("product", "order__customer").annotate(
            line_total=F("quantity") * F("unit_price")
        )
        if is_gestor(self.request.user):
            return qs
        return qs.filter(order__customer__user=self.request.user)

    def perform_create(self, serializer):
        # só se pode acrescentar linhas às próprias encomendas pendentes
        # lines can only be added to your own pending orders
        order = serializer.validated_data["order"]
        if not is_gestor(self.request.user) and order.customer.user_id != self.request.user.id:
            raise NotFound()
        if order.status != Order.Status.PENDING:
            raise Conflict(f"Order #{order.pk} is {order.status}.")
        serializer.save()


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.none()  # schema only · the real one is get_queryset
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["order", "method"]

    def get_queryset(self):
        qs = Payment.objects.select_related("order__customer")
        if is_gestor(self.request.user):
            return qs
        return qs.filter(order__customer__user=self.request.user)


class OrdersReportView(APIView):
    """POST /api/v1/reports/orders/ → 202 + onde perguntar pelo estado · 202 + where to poll."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={202: TaskAcceptedSerializer})
    def post(self, request):
        if is_gestor(request.user):
            customer_id = None  # todas · everyone's
        else:
            customer, _ = Customer.objects.get_or_create(user=request.user)
            customer_id = customer.id
        result = export_orders_report.delay(request.user.id, customer_id)
        # quem pode ler o estado desta tarefa · who may read this task's status (Redis como KV)
        cache.set(f"task:{result.id}:owner", request.user.id, timeout=3600)
        status_url = reverse("task-status", args=[result.id])
        return Response(
            {"id": result.id, "status_url": status_url},
            status=status.HTTP_202_ACCEPTED,
            headers={"Location": status_url},
        )


class TaskStatusView(APIView):
    """GET /api/v1/tasks/<id>/ — o estado de uma tarefa minha · one of my tasks' state."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: TaskStatusSerializer, 404: OpenApiResponse()})
    def get(self, request, task_id: str):
        owner = cache.get(f"task:{task_id}:owner")
        if owner is None or (owner != request.user.id and not is_gestor(request.user)):
            raise NotFound()  # desconhecida ou alheia → 404, como as encomendas · unknown/foreign
        result = AsyncResult(task_id)
        body = {
            "id": task_id,
            "state": result.state,
            "progress": None,
            "result": None,
            "error": None,
        }
        if result.state == "PROGRESS":
            body["progress"] = result.info
        elif result.successful():
            body["result"] = result.result
        elif result.failed():
            body["error"] = str(result.result)
        return Response(body)
