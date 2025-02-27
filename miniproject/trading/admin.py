from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import Order, Transaction, OrderBook, PriceHistory, Notification


class TransactionInline(admin.TabularInline):
    model = Transaction
    fk_name = 'order'
    extra = 0
    readonly_fields = ("executed_at", "transaction_id", "executed_by", "order_link", "counter_order_link")
    fields = ("transaction_id", "executed_price", "quantity", "transaction_fee", "executed_at", "executed_by", "order_link", "counter_order_link")

    def order_link(self, obj):
        if obj.order:
            url = reverse("admin:trading_order_change", args=[obj.order.id])
            return mark_safe(f'<a href="{url}">Order #{obj.order.id}</a>')
        return "-"

    def counter_order_link(self, obj):
        if obj.counter_order:
            url = reverse("admin:trading_order_change", args=[obj.counter_order.id])
            return mark_safe(f'<a href="{url}">Order #{obj.counter_order.id}</a>')
        return "-"

    order_link.short_description = "Order"
    counter_order_link.short_description = "Counter Order"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "product_link",
        "order_type",
        "price",
        "quantity",
        "filled_quantity",
        "remaining_quantity",
        "status",
        "created_at",
    )
    list_filter = (
        "order_type",
        "status",
        "time_in_force",
        "requires_approval",
        "created_at"
    )
    search_fields = ("id", "user__username", "product__name", "notes")
    readonly_fields = (
        "created_at",
        "updated_at",
        "filled_quantity",
        "remaining_quantity",
        "approved_by",
        "approved_at"
    )
    autocomplete_fields = ("user", "product")
    inlines = [TransactionInline]
    date_hierarchy = "created_at"

    fieldsets = (
        (None, {
            'fields': ('user', 'product', 'order_type', 'quantity', 'price')
        }),
        ('Status', {
            'fields': ('status', 'filled_quantity', 'remaining_quantity')
        }),
        ('Time Settings', {
            'fields': ('time_in_force', 'expires_at')
        }),
        ('Approval', {
            'fields': ('requires_approval', 'approved_by', 'approved_at', 'rejection_reason')
        }),
        ('Additional Information', {
            'fields': ('notes', 'ip_address', 'created_at', 'updated_at')
        }),
    )

    def product_link(self, obj):
        if obj.product:
            url = reverse("admin:products_product_change", args=[obj.product.id])
            return mark_safe(f'<a href="{url}">{obj.product.name}</a>')
        return "-"

    product_link.short_description = "Product"

    actions = ['approve_orders', 'cancel_orders', 'mark_as_expired']

    def approve_orders(self, request, queryset):
        updated = 0
        for order in queryset.filter(status='pending'):
            order.approve(request.user)
            updated += 1
        self.message_user(request, f"{updated} orders were approved.")

    def cancel_orders(self, request, queryset):
        updated = 0
        for order in queryset.filter(status__in=['active', 'partially_filled', 'pending']):
            order.cancel("Cancelled by admin")
            updated += 1
        self.message_user(request, f"{updated} orders were cancelled.")

    def mark_as_expired(self, request, queryset):
        updated = 0
        for order in queryset.filter(status__in=['active', 'partially_filled', 'pending']):
            order.status = 'expired'
            order.save()
            updated += 1
        self.message_user(request, f"{updated} orders were marked as expired.")

    approve_orders.short_description = "Approve selected orders"
    cancel_orders.short_description = "Cancel selected orders"
    mark_as_expired.short_description = "Mark selected orders as expired"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "transaction_id",
        "order_link",
        "counter_order_link",
        "product_name",
        "executed_price",
        "quantity",
        "transaction_fee",
        "executed_at",
    )
    list_filter = ("executed_at", "executed_by")
    search_fields = (
        "transaction_id",
        "order__user__username",
        "order__product__name",
        "notes"
    )
    readonly_fields = ("executed_at", "transaction_id")
    autocomplete_fields = ("order", "counter_order", "executed_by")
    date_hierarchy = "executed_at"

    def order_link(self, obj):
        if obj.order:
            url = reverse("admin:trading_order_change", args=[obj.order.id])
            return mark_safe(f'<a href="{url}">Order #{obj.order.id}</a>')
        return "-"

    def counter_order_link(self, obj):
        if obj.counter_order:
            url = reverse("admin:trading_order_change", args=[obj.counter_order.id])
            return mark_safe(f'<a href="{url}">Order #{obj.counter_order.id}</a>')
        return "-"

    def product_name(self, obj):
        return obj.order.product.name if obj.order and obj.order.product else "-"

    order_link.short_description = "Order"
    counter_order_link.short_description = "Counter Order"
    product_name.short_description = "Product"


@admin.register(OrderBook)
class OrderBookAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "timestamp",
        "best_bid",
        "best_ask",
        "total_bid_quantity",
        "total_ask_quantity",
    )
    list_filter = ("timestamp", "product")
    search_fields = ("product__name",)
    readonly_fields = ("timestamp",)
    date_hierarchy = "timestamp"


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "timestamp",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
    )
    list_filter = ("timestamp", "product")
    search_fields = ("product__name",)
    readonly_fields = ("timestamp",)
    date_hierarchy = "timestamp"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "notification_type",
        "related_order_link",
        "created_at",
        "read",
    )
    list_filter = ("notification_type", "created_at", "read")
    search_fields = ("user__username", "message")
    readonly_fields = ("created_at",)
    list_editable = ("read",)

    def related_order_link(self, obj):
        if obj.related_order:
            url = reverse("admin:trading_order_change", args=[obj.related_order.id])
            return mark_safe(f'<a href="{url}">Order #{obj.related_order.id}</a>')
        return "-"

    related_order_link.short_description = "Related Order"

    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        queryset.update(read=True)
        self.message_user(request, f"{queryset.count()} notifications were marked as read.")

    def mark_as_unread(self, request, queryset):
        queryset.update(read=False)
        self.message_user(request, f"{queryset.count()} notifications were marked as unread.")

    mark_as_read.short_description = "Mark selected notifications as read"
    mark_as_unread.short_description = "Mark selected notifications as unread"
