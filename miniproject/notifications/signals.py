from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

from .models import Notification, NotificationPreference
from trading.models import Order, Transaction
from sales.models import Invoice

@receiver(post_save, sender=Order)
def order_notification(sender, instance, created, **kwargs):
    """
    Signal handler to create notifications when an order is created or its status changes.
    """
    if created:
        # Order confirmation event (new order placed)
        message = f"Your order #{instance.id} has been placed successfully."
        # Trigger email and push notifications for the user
        Notification.objects.create(user=instance.user, notification_type='email',
                                    message=message, related_order=instance)
        Notification.objects.create(user=instance.user, notification_type='push',
                                    message=message, related_order=instance)
    else:
        # Order status update events (e.g., filled, cancelled, etc.)
        if instance.status in ['filled', 'cancelled', 'rejected', 'expired', 'approved']:
            status_text = instance.status.replace('_', ' ').title()  # e.g. "partially_filled" -> "Partially Filled"
            message = f"Your order #{instance.id} was {status_text}."
            Notification.objects.create(user=instance.user, notification_type='push',
                                        message=message, related_order=instance)
            Notification.objects.create(user=instance.user, notification_type='email',
                                        message=message, related_order=instance)

@receiver(post_save, sender=Transaction)
def transaction_notification(sender, instance, created, **kwargs):
    """
    Signal handler to create notifications when a trade transaction is executed.
    """
    if created:
        order = instance.order
        counter_order = instance.counter_order
        # Notification for the primary order's owner
        if order:
            message = (f"Trade executed: Your {order.order_type} order (#{order.id}) for "
                       f"{instance.quantity} units of {order.product.name} at price {instance.executed_price}.")
            Notification.objects.create(user=order.user, notification_type='push',
                                        message=message, related_order=order)
            Notification.objects.create(user=order.user, notification_type='email',
                                        message=message, related_order=order)
        # Notification for the counter-order's owner
        if counter_order:
            message = (f"Trade executed: Your {counter_order.order_type} order (#{counter_order.id}) for "
                       f"{instance.quantity} units of {counter_order.product.name} at price {instance.executed_price}.")
            Notification.objects.create(user=counter_order.user, notification_type='push',
                                        message=message, related_order=counter_order)
            Notification.objects.create(user=counter_order.user, notification_type='email',
                                        message=message, related_order=counter_order)

@receiver(post_save, sender=Invoice)
def invoice_notification(sender, instance, created, **kwargs):
    """
    Signal handler to create notifications when an invoice is generated.
    """
    if created:
        message = f"Invoice #{instance.id} has been generated."
        # Trigger an email notification (e.g., to send the invoice to the user)
        Notification.objects.create(user=instance.user, notification_type='email',
                                    message=message, related_invoice=instance)
        # Also create a push notification for the user
        Notification.objects.create(user=instance.user, notification_type='push',
                                    message=message, related_invoice=instance)

@receiver(post_save, sender=Notification)
def send_notification_alerts(sender, instance, created, **kwargs):
    """
    Signal handler to send out email or push notifications whenever a Notification object is created.
    """
    if not created:
        return  # Only send alerts for new notifications

    # Fetch user preferences (if exist; assume enabled if not set)
    try:
        prefs = instance.user.notification_preferences
    except NotificationPreference.DoesNotExist:
        prefs = None

    # Send an email using Django's email backend for email-type notifications
    if instance.notification_type == 'email' and (not prefs or prefs.email_notifications):
        subject = "Notification - " + (instance.message[:50] or "Important Update")
        body = instance.message
        recipient_list = [instance.user.email]
        # Ensure EMAIL settings (host, from address) are configured in settings.py
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipient_list, fail_silently=True)

    # Send a push notification via FCM for push-type notifications
    if instance.notification_type == 'push' and (not prefs or prefs.push_notifications):
        device_token = None
        if prefs:
            device_token = prefs.device_token
        if device_token:
            # Construct and send the push notification using Firebase Cloud Messaging
            try:
                from firebase_admin import messaging
                fcm_message = messaging.Message(
                    notification=messaging.Notification(
                        title="New Notification",
                        body=instance.message
                    ),
                    token=device_token
                )
                messaging.send(fcm_message)
            except Exception as e:
                # In a real application, log this exception properly
                print(f"Error sending FCM push notification: {e}")
        else:
            # No device token available for push
            print("No device token; push notification not sent.")
