import django_filters
from django.db.models import Q
from .models import Product, Category, Tag
from products import models


class ProductFilter(django_filters.FilterSet):
    """Advanced filter set for products"""

    # Price range filters
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr='lte')

    # Category filters
    category_name = django_filters.CharFilter(field_name='category__name', lookup_expr='icontains')

    # Tag filters - filter products that have ALL the specified tags
    tag_ids = django_filters.ModelMultipleChoiceFilter(
        field_name='tags',
        queryset=Tag.objects.all(),
        conjoined=True,  # AND logic (must have all tags)
    )

    # Tag filters - filter products that have ANY of the specified tags
    any_tag_ids = django_filters.ModelMultipleChoiceFilter(
        field_name='tags',
        queryset=Tag.objects.all(),
        conjoined=False,  # OR logic (can have any tag)
    )

    # Stock filters
    in_stock = django_filters.BooleanFilter(method='filter_in_stock')
    low_stock = django_filters.BooleanFilter(method='filter_low_stock')

    # Search by name or description or SKU
    search = django_filters.CharFilter(method='filter_search')

    # Created at range
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Product
        fields = [
            'category',
            'min_price',
            'max_price',
            'status',
            'is_tradeable',
            'tag_ids',
            'any_tag_ids',
        ]

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(quantity_in_stock__gt=0)
        return queryset.filter(quantity_in_stock=0)

    def filter_low_stock(self, queryset, name, value):
        if value:
            # Products where quantity is below or equal to reorder threshold
            return queryset.filter(quantity_in_stock__lte=models.F('reorder_threshold'), quantity_in_stock__gt=0)
        return queryset

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset

        # Search in name, description and SKU
        return queryset.filter(
            Q(name__icontains=value) |
            Q(description__icontains=value) |
            Q(sku__icontains=value)
        ).distinct()
