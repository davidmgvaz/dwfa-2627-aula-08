"""Tarefas Celery · Celery tasks (Ficha 05, Aula 07).

PT: tudo o que não cabe num pedido HTTP — enviar um recibo, gerar um relatório —
corre aqui, num worker, com retries e com progresso. Regras: receber ids (nunca
objetos ORM), ser idempotente (o broker entrega *pelo menos uma vez*), avisar o
utilizador quando acaba.
EN: whatever does not fit in an HTTP request — sending a receipt, building a report —
runs here, in a worker, with retries and progress. Rules: take ids (never ORM objects),
be idempotent (the broker delivers *at least once*), tell the user when done.
"""

import time
from decimal import Decimal

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from .models import LINE_TOTAL, Order, Payment
from .notify import notify_user


class ReceiptGatewayError(Exception):
    """O fornecedor de email/recibos falhou de forma transitória · a transient provider failure."""


@shared_task(
    bind=True,
    autoretry_for=(ReceiptGatewayError,),
    retry_backoff=2,  # 2 s, 4 s, 8 s… · exponential backoff
    retry_backoff_max=60,
    retry_jitter=False,  # determinístico para a demo · deterministic for the demo
    max_retries=3,
    acks_late=True,  # a mensagem só sai da fila quando a tarefa acaba · ack after completion
)
def send_order_receipt(self, order_id: int) -> str:
    """Envia o recibo de uma encomenda paga, uma vez · emails the receipt of a paid order, once."""
    with transaction.atomic():
        payment = (
            Payment.objects.select_for_update()
            .select_related("order__customer__user")
            .get(order_id=order_id)
        )
        if payment.receipt_sent_at is not None:
            return (
                "already-sent"  # idempotência: a 2.ª entrega não faz nada · 2nd delivery is a no-op
            )
        # Simula um fornecedor instável: falha na 1.ª tentativa quando RECEIPT_FLAKY=1
        # Simulates a flaky provider: fails on the 1st attempt when RECEIPT_FLAKY=1
        if settings.RECEIPT_FLAKY and self.request.retries == 0:
            raise ReceiptGatewayError("receipt provider timed out")
        user = payment.order.customer.user
        send_mail(
            subject=f"Receipt for order #{order_id}",
            message=f"Thank you, {user.get_username()}. We received {payment.amount} €.",
            from_email=None,
            recipient_list=[user.email or f"{user.get_username()}@example.com"],
        )
        payment.receipt_sent_at = timezone.now()
        payment.save(update_fields=["receipt_sent_at"])
        user_id = user.id
    # fora da transação: o aviso só sai se o commit aconteceu · outside: only after the commit
    notify_user(user_id, "order.paid", order_id=order_id, amount=str(payment.amount))
    return "sent"


@shared_task(bind=True)
def export_orders_report(self, user_id: int, customer_id: int | None) -> dict:
    """Resumo das encomendas (de um cliente, ou de todos para um gestor), com progresso.
    Order summary (one customer's, or everyone's for a manager), reporting progress."""
    qs = Order.objects.annotate(total=Sum(LINE_TOTAL)).order_by("id")
    if customer_id is not None:
        qs = qs.filter(customer_id=customer_id)
    total = qs.count()
    summary = {"orders": 0, "amount": Decimal("0.00"), "by_status": {}}
    for i, order in enumerate(qs.iterator(chunk_size=50), start=1):
        summary["orders"] += 1
        summary["amount"] += order.total or 0
        summary["by_status"][order.status] = summary["by_status"].get(order.status, 0) + 1
        time.sleep(settings.REPORT_STEP_SECONDS)  # simula trabalho real · stands in for real work
        # estado intermédio visível em GET /api/v1/tasks/<id>/ · visible in the status endpoint
        self.update_state(state="PROGRESS", meta={"current": i, "total": total})
    summary["amount"] = str(summary["amount"])  # JSON: Decimal → string (como o DRF)
    notify_user(user_id, "report.ready", task_id=self.request.id, orders=summary["orders"])
    return summary


# usado nos testes e na demo · used by tests and the demo
__all__ = ["send_order_receipt", "export_orders_report", "ReceiptGatewayError", "F"]
