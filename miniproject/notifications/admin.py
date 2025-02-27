from django.contrib import admin
from django.utils.safestring import mark_safe
from django.urls import reverse

from .models import Notification, NotificationPreference

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'notification_type', 'related_order_link',
                    'related_invoice_link', 'created_at', 'read')
    list_filter = ('notification_type', 'read', 'created_at')
    search_fields = ('user__username', 'user__email', 'message')
    readonly_fields = ('created_at',)
    list_editable = ('read',)
    actions = ['mark_as_read', 'mark_as_unread']

    def related_order_link(self, obj):
        if obj.related_order:
            url = reverse("admin:trading_order_change", args=[obj.related_order.id])
            return mark_safe(f'<a href="{url}">Order #{obj.related_order.id}</a>')
        return "-"
    related_order_link.short_description = "Related Order"

    def related_invoice_link(self, obj):
        if obj.related_invoice:
            url = reverse("admin:sales_invoice_change", args=[obj.related_invoice.id])
            return mark_safe(f'<a href="{url}">Invoice #{obj.related_invoice.id}</a>')
        return "-"
    related_invoice_link.short_description = "Related Invoice"

    def mark_as_read(self, request, queryset):
        queryset.update(read=True)
        self.message_user(request, f"{queryset.count()} notifications were marked as read.")
    def mark_as_unread(self, request, queryset):
        queryset.update(read=False)
        self.message_user(request, f"{queryset.count()} notifications were marked as unread.")
    mark_as_read.short_description = "Mark selected notifications as read"
    mark_as_unread.short_description = "Mark selected notifications as unread"

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_notifications', 'push_notifications', 'device_token')
    search_fields = ('user__username', 'user__email')
