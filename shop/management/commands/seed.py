"""`manage.py seed` — dados de demonstração, idempotente · demo data, idempotent.

PT: correr duas vezes dá o mesmo resultado — as factories usam `django_get_or_create`
em slug/sku/user e as encomendas são identificadas por um cliente fixo.
EN: running it twice yields the same state — factories use `django_get_or_create`
on slug/sku/user and the orders hang off fixed customers.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.factories import UserFactory
from shop.factories import CategoryFactory, CustomerFactory, OrderItemFactory, ProductFactory
from shop.models import Order

CATEGORIES = ["lamps", "chairs", "tables", "rugs"]
CUSTOMERS = ["ana", "bruno", "carla"]
COLORS = ["red", "black", "white", "oak"]
# Ficha 05: atributos JSONB por categoria, sem esquema fixo · per-category JSONB attributes
ATTRIBUTES = {
    "lamps": lambda i: {
        "color": COLORS[(i // 4) % 4],
        "bulb": "E27",
        "watts": 40 + 20 * ((i // 4) % 3),
    },
    "chairs": lambda i: {
        "color": COLORS[(i // 4) % 4],
        "material": ["wood", "steel"][(i // 4) % 2],
    },
    "tables": lambda i: {
        "material": ["wood", "glass", "steel"][(i // 4) % 3],
        "seats": 2 + 2 * ((i // 4) % 3),
    },
    "rugs": lambda i: {"color": COLORS[(i // 4) % 4], "size": ["S", "M", "L"][(i // 4) % 3]},
}


class Command(BaseCommand):
    help = "Seed demo data (idempotent)"

    @transaction.atomic
    def handle(self, *args, **options):
        categories = [CategoryFactory(slug=slug, name=slug.capitalize()) for slug in CATEGORIES]
        products = []
        for i in range(40):
            category = categories[i % len(categories)]
            product = ProductFactory(sku=f"SKU-{i:05d}", category=category)
            product.attributes = ATTRIBUTES[category.slug](i)
            product.save(update_fields=["attributes"])
            products.append(product)
        customers = [
            CustomerFactory(user=UserFactory(username=name, email=f"{name}@example.com"))
            for name in CUSTOMERS
        ]
        created = 0
        for customer in customers:
            # 10 encomendas por cliente, só na 1.ª vez · 10 orders per customer, first run only
            missing = 10 - customer.orders.count()
            for n in range(missing):
                order = Order.objects.create(customer=customer)
                for k in range(3):
                    OrderItemFactory(order=order, product=products[(n * 3 + k) % len(products)])
                created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"seed: {len(categories)} categories, {len(products)} products, "
                f"{len(customers)} customers, {created} new orders "
                f"({Order.objects.count()} total)"
            )
        )
