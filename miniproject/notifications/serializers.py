from rest_framework import serializers
from .models import Notification, NotificationPreference

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'notification_type', 'message',
            'related_order', 'related_invoice', 'created_at', 'read'
        ]
        read_only_fields = ['id', 'user', 'notification_type',
                            'message', 'related_order', 'related_invoice', 'created_at']
        # 'read' is not read_only, allowing the client to mark notifications as read.

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ['email_notifications', 'push_notifications', 'device_token']
        # The user field is implicit; we manage preferences per current user only.
