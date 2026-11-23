"""Regras de negócio fora das vistas · business rules outside the views.

PT: a vista fica fina; a transição de estado corre numa transação com
`select_for_update` — dois `pay` concorrentes não pagam a mesma encomenda duas vezes.
EN: the view stays thin; the state transition runs in a transaction with
`select_for_update` — two concurrent `pay` calls cannot pay the same order twice.
"""

from django.db import transaction
from django.db.models import F, Sum
from rest_framework import status
from rest_framework.exceptions import APIException

from .models import Order, Payment
from .tasks import send_order_receipt


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The operation conflicts with the current state of the resource."
    default_code = "conflict"


def order_total(order: Order):
    return order.items.aggregate(total=Sum(F("quantity") * F("unit_price")))["total"] or 0


@transaction.atomic
def pay_order(order: Order, method: str = Payment.Method.CARD) -> Order:
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status != Order.Status.PENDING:
        raise Conflict(f"Order #{order.pk} is {order.status}; only pending orders can be paid.")
    total = order_total(order)
    if total <= 0:
        raise Conflict(f"Order #{order.pk} has no items.")
    Payment.objects.create(order=order, amount=total, method=method)
    order.status = Order.Status.PAID
    order.save(update_fields=["status"])
    # Ficha 05: o recibo sai num worker, e só DEPOIS do commit — um `.delay()` aqui dentro
    # podia correr antes de a linha existir para o worker (ou depois de um rollback).
    # Ficha 05: the receipt goes out in a worker, and only AFTER the commit — a `.delay()` in
    # here could run before the row is visible to the worker (or after a rollback).
    transaction.on_commit(lambda: send_order_receipt.delay(order.pk))
    return order


@transaction.atomic
def cancel_order(order: Order) -> Order:
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status != Order.Status.PENDING:
        raise Conflict(
            f"Order #{order.pk} is {order.status}; only pending orders can be cancelled."
        )
    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status"])
    return order
