"""Ficha 05, parte 4 (+ opcional) — JSONB com GIN, cache do catálogo com invalidação.
Ficha 05, part 4 (+ optional) — JSONB with GIN, catalogue cache with invalidation."""

import pytest
from django.core.cache import cache
from django.db import connection
from rest_framework.test import APIClient

from shop.factories import CategoryFactory, ProductFactory
from shop.models import Product


@pytest.mark.django_db
def test_attr_filter_uses_jsonb_containment():
    red = ProductFactory(attributes={"color": "red", "material": "wood"})
    ProductFactory(attributes={"color": "black"})
    ProductFactory(attributes={})
    r = APIClient().get("/api/v1/products/?attr=color:red")
    assert r.status_code == 200
    assert [p["id"] for p in r.json()["results"]] == [red.id]
    assert APIClient().get("/api/v1/products/?attr=nonsense").json()["count"] == 0
    # o lookup é containment (@>), não igualdade de texto · containment, not text equality
    assert Product.objects.filter(attributes__contains={"material": "wood"}).count() == 1


@pytest.mark.django_db
def test_attributes_have_a_gin_index():
    with connection.cursor() as cur:
        indexes = connection.introspection.get_constraints(cur, Product._meta.db_table)
    gin = indexes["product_attributes_gin"]
    assert gin["type"] == "gin" and gin["columns"] == ["attributes"]


@pytest.mark.django_db
def test_category_list_is_cached_and_invalidated_on_write():
    cache.clear()
    CategoryFactory(name="Lamps", slug="lamps")
    api = APIClient()
    first = api.get("/api/v1/categories/")
    assert first.status_code == 200 and first["X-Cache"] == "MISS"
    second = api.get("/api/v1/categories/")
    assert second["X-Cache"] == "HIT" and second.json() == first.json()
    assert api.get("/api/v1/categories/?search=lam")["X-Cache"] == "MISS"  # outro URL, outra chave

    CategoryFactory(name="Rugs", slug="rugs")  # post_save → versão nova · new version
    third = api.get("/api/v1/categories/")
    assert third["X-Cache"] == "MISS" and third.json()["count"] == 2
