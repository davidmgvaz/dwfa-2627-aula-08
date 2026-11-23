"""Ficha 05, partes 1–2 — tarefas: idempotência, retry, progresso, estado por dono.
Ficha 05, parts 1–2 — tasks: idempotency, retry, progress, owner-scoped status."""

from decimal import Decimal

import pytest
from django.core import mail

from shop.factories import OrderFactory, OrderItemFactory, PaymentFactory, ProductFactory
from shop.models import Order, Payment
from shop.services import pay_order
from shop.tasks import export_orders_report, send_order_receipt

from .conftest import as_


@pytest.mark.django_db
def test_pay_enqueues_receipt_after_commit(
    actors, customer_api, django_capture_on_commit_callbacks
):
    order = OrderFactory(customer=actors["customer"].customer)
    OrderItemFactory(order=order, product=ProductFactory(price=Decimal("10.00")), quantity=2)
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        r = customer_api.post(f"/api/v1/orders/{order.id}/pay/")
    assert r.status_code == 200 and r.json()["status"] == "paid"
    assert len(callbacks) == 1  # o .delay() ficou para depois do commit · deferred to on_commit
    payment = Payment.objects.get(order=order)
    assert payment.receipt_sent_at is not None  # eager: a tarefa já correu · task already ran
    assert len(mail.outbox) == 1 and "20.00" in mail.outbox[0].body


@pytest.mark.django_db
def test_receipt_is_idempotent():
    payment = PaymentFactory(amount=Decimal("5.00"))
    assert send_order_receipt.delay(payment.order_id).get() == "sent"
    assert send_order_receipt.delay(payment.order_id).get() == "already-sent"  # 2.ª entrega
    assert len(mail.outbox) == 1  # um recibo, não dois · one receipt, not two


@pytest.mark.django_db
def test_receipt_retries_on_transient_failure(settings):
    settings.RECEIPT_FLAKY = True  # a 1.ª tentativa falha; o retry (eager) corre logo
    payment = PaymentFactory(amount=Decimal("5.00"))
    # em modo eager o retry corre logo a seguir, no mesmo processo · eager: the retry runs inline
    send_order_receipt.apply(args=[payment.order_id], throw=False)
    payment.refresh_from_db()
    assert payment.receipt_sent_at is not None and len(mail.outbox) == 1


@pytest.mark.django_db
def test_report_counts_only_my_orders_and_reports_progress(actors):
    mine = actors["customer"].customer
    for _ in range(3):
        OrderItemFactory(
            order=OrderFactory(customer=mine), product=ProductFactory(price=Decimal("2.00"))
        )
    OrderFactory.create_batch(2)  # de outros · other people's
    result = export_orders_report.delay(actors["customer"].id, mine.id)
    summary = result.get()
    assert summary["orders"] == 3 and summary["by_status"] == {"pending": 3}
    assert Decimal(summary["amount"]) > 0
    assert result.state == "SUCCESS"


@pytest.mark.django_db
@pytest.mark.parametrize("role,expected", [("anon", 401), ("customer", 202), ("gestor", 202)])
def test_report_endpoint_returns_202_with_status_url(actors, role, expected):
    r = as_(actors[role]).post("/api/v1/reports/orders/")
    assert r.status_code == expected
    if expected == 202:
        body = r.json()
        assert body["status_url"] == f"/api/v1/tasks/{body['id']}/" == r["Location"]


@pytest.mark.django_db
def test_task_status_is_scoped_to_its_owner(actors):
    OrderFactory(customer=actors["customer"].customer)
    api = as_(actors["customer"])
    task_id = api.post("/api/v1/reports/orders/").json()["id"]
    r = api.get(f"/api/v1/tasks/{task_id}/")
    assert r.status_code == 200
    assert r.json()["state"] == "SUCCESS" and r.json()["result"]["orders"] == 1
    other = OrderFactory().customer.user
    assert as_(other).get(f"/api/v1/tasks/{task_id}/").status_code == 404  # alheia · foreign
    assert as_(actors["gestor"]).get(f"/api/v1/tasks/{task_id}/").status_code == 200
    assert api.get("/api/v1/tasks/does-not-exist/").status_code == 404


@pytest.mark.django_db
def test_paid_order_keeps_working_for_the_spa(actors):
    # a Ficha 04 continua a funcionar: pay → paid, 2.º pay → 409 · Ficha 04 still holds
    order = OrderFactory(customer=actors["customer"].customer)
    OrderItemFactory(order=order, product=ProductFactory(price=Decimal("1.00")))
    pay_order(order)
    order.refresh_from_db()
    assert order.status == Order.Status.PAID
    assert as_(actors["customer"]).post(f"/api/v1/orders/{order.id}/pay/").status_code == 409
