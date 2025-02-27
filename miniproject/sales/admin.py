from django.contrib import admin
from .models import Invoice, SalesOrder, SalesOrderItem

class SalesOrderItemInline(admin.TabularInline):
    model = SalesOrderItem
    extra = 1
    readonly_fields = ("subtotal",)
    autocomplete_fields = ("product",)
    fields = ("product", "quantity", "price", "subtotal")

@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "status",
        "discount_percent",
        "total",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("id", "customer__username")
    readonly_fields = ("created_at", "total")
    inlines = [SalesOrderItemInline]
    autocomplete_fields = ("customer",)

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "sales_order", "invoice_date", "order_total")
    readonly_fields = ("invoice_date", "order_total")
    search_fields = ("sales_order__id", "sales_order__customer__username")
    autocomplete_fields = ("sales_order",)

    def order_total(self, obj):
        return obj.sales_order.total
    order_total.short_description = "Order Total"
