import django_filters

from .models import Order, Product


class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    in_stock = django_filters.BooleanFilter(field_name="stock", lookup_expr="gt", exclude=False)
    # Ficha 05: `?attr=color:red` → attributes @> '{"color": "red"}' (JSONB, índice GIN)
    attr = django_filters.CharFilter(
        method="filter_attr", help_text="key:value inside `attributes`, e.g. color:red"
    )

    def filter_attr(self, queryset, name, value):
        key, sep, val = value.partition(":")
        if not sep or not key:
            return queryset.none()
        # containment (`@>`) em vez de `attributes__color=…`: a chave vem do cliente e um
        # lookup dinâmico (`attributes__{key}`) aceitaria `color__gt`; o dicionário não
        # containment (`@>`) instead of `attributes__color=…`: the key comes from the client and a
        # dynamic lookup (`attributes__{key}`) would accept `color__gt`; the dict does not
        return queryset.filter(attributes__contains={key: val})

    class Meta:
        model = Product
        fields = ["category", "is_active", "min_price", "max_price", "attr"]


class OrderFilter(django_filters.FilterSet):
    created_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Order
        fields = ["status", "customer", "created_from", "created_to"]
