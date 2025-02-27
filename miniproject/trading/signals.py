from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import Order, Transaction, Notification
from .utils import attempt_to_match_order


@receiver(post_save, sender=Order)
def order_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for Order post_save events
    """
    # If a new active order is created, try to match it
    if created and instance.status == 'active':
        attempt_to_match_order(instance)

    # If an order is updated to active, try to match it
    elif not created and instance.status == 'active' and instance.remaining_quantity > 0:
        attempt_to_match_order(instance)


@receiver(post_save, sender=Transaction)
def transaction_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for Transaction post_save events
    """
    if created:
        # Update related orders' status
        order = instance.order
        if order:
            executed_quantity = instance.quantity
            if order.remaining_quantity > 0:
                # Update order status
                order.filled_quantity += executed_quantity
                order.remaining_quantity = max(0, order.quantity - order.filled_quantity)

                if order.filled_quantity >= order.quantity:
                    order.status = 'filled'
                elif order.filled_quantity > 0:
                    order.status = 'partially_filled'

                order.save(update_fields=['filled_quantity', 'remaining_quantity', 'status'])

        counter_order = instance.counter_order
        if counter_order:
            executed_quantity = instance.quantity
            if counter_order.remaining_quantity > 0:
                # Update counter order status
                counter_order.filled_quantity += executed_quantity
                counter_order.remaining_quantity = max(0, counter_order.quantity - counter_order.filled_quantity)

                if counter_order.filled_quantity >= counter_order.quantity:
                    counter_order.status = 'filled'
                elif counter_order.filled_quantity > 0:
                    counter_order.status = 'partially_filled'

                counter_order.save(update_fields=['filled_quantity', 'remaining_quantity', 'status'])


@receiver(post_save, sender=Notification)
def notification_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for Notification post_save events

    In a real application, this would trigger email/push notifications
    """
    if created:
        # In a real application, this would send an email or push notification
        # For now, we'll just print a message
        print(f"NOTIFICATION: {instance.notification_type} for {instance.user.username}: {instance.message}")
