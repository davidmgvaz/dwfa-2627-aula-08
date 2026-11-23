import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from shop.factories import CustomerFactory


@pytest.fixture
def actors(db):
    """anon · customer · gestor — the three columns of the matrix."""
    gestor = UserFactory()
    # criado pela migração 0002; get_or_create porque os testes transacionais (WebSocket)
    # fazem flush à base de dados · created by migration 0002; get_or_create because the
    # transactional (WebSocket) tests flush the database
    gestor.groups.add(Group.objects.get_or_create(name="gestores")[0])
    customer = CustomerFactory().user
    return {"anon": None, "customer": customer, "gestor": gestor}


def as_(user):
    api = APIClient()
    if user:
        api.force_authenticate(user=user)
    return api


@pytest.fixture
def customer_api(actors):
    return as_(actors["customer"])
