from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal

from products.models import Product


class Order(models.Model):
    ORDER_TYPE_CHOICES = (
        ("buy", "Buy"),
        ("sell", "Sell"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending Approval"),
        ("active", "Active"),
        ("partially_filled", "Partially Filled"),
        ("filled", "Filled"),
        ("cancelled", "Cancelled"),
        ("rejected", "Rejected"),
        ("expired", "Expired"),
    )

    ORDER_TIME_CHOICES = (
        ("day", "Day Order"),
        ("gtc", "Good Till Cancelled"),
        ("gtd", "Good Till Date"),
    )

    # Basic Order Information
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="orders")
    order_type = models.CharField(max_length=4, choices=ORDER_TYPE_CHOICES)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])

    # Order Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    filled_quantity = models.PositiveIntegerField(default=0)
    remaining_quantity = models.PositiveIntegerField(default=0)

    # Order Time Settings
    time_in_force = models.CharField(max_length=3, choices=ORDER_TIME_CHOICES, default="day")
    expires_at = models.DateTimeField(null=True, blank=True)

    # Order Approval (if needed)
    requires_approval = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_orders"
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # Rejection Information
    rejection_reason = models.TextField(blank=True, null=True)

    # Meta Information
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.order_type.upper()} #{self.id} - {self.product.name} x {self.quantity}"

    def save(self, *args, **kwargs):
        # Initialize remaining_quantity on create
        if not self.pk:
            self.remaining_quantity = self.quantity

        # Calculate expiration date for GTD orders
        if self.time_in_force == 'day' and not self.expires_at:
            # Set to end of trading day (e.g., 4:00 PM)
            now = timezone.now()
            self.expires_at = now.replace(hour=16, minute=0, second=0, microsecond=0)
            if now.hour >= 16:  # If it's already past 4 PM, set to next day
                self.expires_at += timezone.timedelta(days=1)

        super().save(*args, **kwargs)

    def cancel(self, reason=None):
        """Cancel this order"""
        if self.status in ['active', 'partially_filled', 'pending']:
            self.status = 'cancelled'
            if reason:
                self.rejection_reason = reason
            self.save()
            return True
        return False

    def approve(self, approver):
        """Approve a pending order"""
        if self.status == 'pending':
            self.status = 'active'
            self.approved_by = approver
            self.approved_at = timezone.now()
            self.save()
            return True
        return False

    def reject(self, reason):
        """Reject a pending order"""
        if self.status == 'pending':
            self.status = 'rejected'
            self.rejection_reason = reason
            self.save()
            return True
        return False

    def update_after_transaction(self, quantity_executed):
        """Update order status after a transaction"""
        self.filled_quantity += quantity_executed
        self.remaining_quantity = self.quantity - self.filled_quantity

        if self.filled_quantity == self.quantity:
            self.status = 'filled'
        elif self.filled_quantity > 0:
            self.status = 'partially_filled'

        self.save()


class Transaction(models.Model):
    """Record of executed trades"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="transactions")
    counter_order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="counter_transactions",
        null=True,
        blank=True
    )
    executed_at = models.DateTimeField(auto_now_add=True)
    executed_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    transaction_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Additional metadata
    transaction_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="executed_transactions"
    )
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Transaction #{self.id} for Order #{self.order.id}"

    def save(self, *args, **kwargs):
        # Generate a transaction ID if not provided
        if not self.transaction_id:
            import uuid
            self.transaction_id = str(uuid.uuid4())[:8].upper()

        if not self.executed_by and self.order.approved_by:
            self.executed_by = self.order.approved_by

        super().save(*args, **kwargs)


class OrderBook(models.Model):
    """Snapshot of the order book for a product at a point in time"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="order_books")
    timestamp = models.DateTimeField(auto_now_add=True)

    # Best bid/ask
    best_bid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    best_ask = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Volume
    total_bid_quantity = models.PositiveIntegerField(default=0)
    total_ask_quantity = models.PositiveIntegerField(default=0)

    # Depth data as JSON
    bid_levels = models.JSONField(default=dict)
    ask_levels = models.JSONField(default=dict)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Order Book for {self.product.name} at {self.timestamp}"


class PriceHistory(models.Model):
    """Historical price data for products"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="price_history")
    timestamp = models.DateTimeField(auto_now_add=True)
    open_price = models.DecimalField(max_digits=10, decimal_places=2)
    high_price = models.DecimalField(max_digits=10, decimal_places=2)
    low_price = models.DecimalField(max_digits=10, decimal_places=2)
    close_price = models.DecimalField(max_digits=10, decimal_places=2)
    volume = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Price histories"

    def __str__(self):
        return f"Price data for {self.product.name} at {self.timestamp}"


class Notification(models.Model):
    """Trading-related notifications for users"""
    NOTIFICATION_TYPES = (
        ('order_executed', 'Order Executed'),
        ('order_cancelled', 'Order Cancelled'),
        ('order_expired', 'Order Expired'),
        ('order_rejected', 'Order Rejected'),
        ('order_approved', 'Order Approved'),
        ('price_alert', 'Price Alert'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trading_notifications")
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    related_order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="trading_notifications_related_order",)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} for {self.user.username}"
