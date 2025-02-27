from django.conf import settings
from django.db import models

class Notification(models.Model):
    """Notification record for a user (email or push notification)."""
    EMAIL = 'email'
    PUSH = 'push'
    NOTIFICATION_TYPE_CHOICES = [
        (EMAIL, 'Email'),
        (PUSH, 'Push'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications'
    )
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPE_CHOICES)
    message = models.TextField()
    # Optional references to related objects in Sales/Trading apps
    related_order = models.ForeignKey('trading.Order', null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name="notifications_related_order", help_text="Related order if applicable")
    related_invoice = models.ForeignKey('sales.Invoice', null=True, blank=True,
                                        on_delete=models.SET_NULL, help_text="Related invoice if applicable")
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']  # latest notifications first

    def __str__(self):
        return f"{self.notification_type.title()} notification for {self.user.username}: {self.message[:20]}..."

class NotificationPreference(models.Model):
    """User preferences for receiving email/push notifications."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences'
    )
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    device_token = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="FCM device token for push notifications"
    )

    def __str__(self):
        return f"Notification Preferences for {self.user.username}"
