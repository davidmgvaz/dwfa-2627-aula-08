from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    CustomerViewSet,
    OrderItemViewSet,
    OrdersReportView,
    OrderViewSet,
    PaymentViewSet,
    ProductViewSet,
    TaskStatusView,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet)
router.register("products", ProductViewSet)
router.register("customers", CustomerViewSet)
router.register(
    "orders", OrderViewSet, basename="order"
)  # sem atributo queryset · no queryset attr
router.register("order-items", OrderItemViewSet, basename="orderitem")
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    # Ficha 05 — 202 Accepted + estado da tarefa · 202 Accepted + task status
    path("reports/orders/", OrdersReportView.as_view(), name="orders-report"),
    path("tasks/<str:task_id>/", TaskStatusView.as_view(), name="task-status"),
    *router.urls,
]
