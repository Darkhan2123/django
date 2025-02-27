from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model

from products.models import Product
from products.serializers import ProductListSerializer
from .models import Order, Transaction, OrderBook, PriceHistory, Notification

User = get_user_model()


class TransactionSerializer(serializers.ModelSerializer):
    order_type = serializers.CharField(source='order.order_type', read_only=True)
    product_name = serializers.CharField(source='order.product.name', read_only=True)
    user = serializers.CharField(source='order.user.username', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id',
            'transaction_id',
            'order',
            'counter_order',
            'executed_at',
            'executed_price',
            'quantity',
            'transaction_fee',
            'executed_by',
            'notes',
            'order_type',
            'product_name',
            'user'
        ]
        read_only_fields = ['executed_at', 'transaction_id', 'executed_by']


class OrderListSerializer(serializers.ModelSerializer):
    """Serializer for listing orders (lighter version)"""
    username = serializers.CharField(source='user.username', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'username',
            'product_name',
            'order_type',
            'price',
            'quantity',
            'filled_quantity',
            'remaining_quantity',
            'status',
            'status_display',
            'created_at'
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for orders with related data"""
    transactions = TransactionSerializer(many=True, read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    product_details = ProductListSerializer(source='product', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    time_in_force_display = serializers.CharField(source='get_time_in_force_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'user',
            'username',
            'product',
            'product_details',
            'order_type',
            'quantity',
            'price',
            'filled_quantity',
            'remaining_quantity',
            'status',
            'status_display',
            'time_in_force',
            'time_in_force_display',
            'expires_at',
            'requires_approval',
            'approved_by',
            'approved_at',
            'rejection_reason',
            'created_at',
            'updated_at',
            'notes',
            'transactions'
        ]
        read_only_fields = [
            'user',
            'filled_quantity',
            'remaining_quantity',
            'status',
            'approved_by',
            'approved_at',
            'created_at',
            'updated_at'
        ]

    def validate(self, data):
        """Additional validation for orders"""
        # Check if product is tradeable
        product = data.get('product')
        if product and not product.is_tradeable:
            raise serializers.ValidationError({"product": "This product is not available for trading."})

        # Check quantity against available stock for sell orders
        order_type = data.get('order_type')
        quantity = data.get('quantity', 0)
        user = self.context['request'].user

        if order_type == 'sell':
            # In a real system, you'd check if the user owns enough of the product to sell
            # This is a simplified check
            pass

        # Check if price is reasonable (e.g., within 20% of last price)
        price = data.get('price', 0)
        if product:
            last_price = PriceHistory.objects.filter(product=product).order_by('-timestamp').first()
            if last_price:
                if price < last_price.close_price * 0.8 or price > last_price.close_price * 1.2:
                    # Just a warning, not an error
                    pass

        # Check if order expires_at is in the future for GTD orders
        time_in_force = data.get('time_in_force')
        expires_at = data.get('expires_at')

        if time_in_force == 'gtd' and expires_at and expires_at <= timezone.now():
            raise serializers.ValidationError({"expires_at": "Expiration date must be in the future."})

        return data

    def create(self, validated_data):
        user = self.context['request'].user

        # Check if user has trader role
        if hasattr(user, 'role') and user.role not in ['trader', 'admin']:
            raise serializers.ValidationError({"user": "Only traders can place orders."})

        # Set IP address if available
        request = self.context.get('request')
        ip_address = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')

        # Create the order
        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                ip_address=ip_address,
                **validated_data
            )

            # Check if order requires approval based on business rules
            if validated_data.get('quantity', 0) > 1000 or validated_data.get('price', 0) > 10000:
                order.requires_approval = True
                order.save()

                # Create notification for admins about approval needed
                admin_users = User.objects.filter(is_staff=True)
                for admin in admin_users:
                    Notification.objects.create(
                        user=admin,
                        notification_type='order_approval',
                        message=f"Order #{order.id} requires your approval",
                        related_order=order
                    )

            # If no approval required, set to active
            elif not order.requires_approval:
                order.status = 'active'
                order.save()

            return order


class OrderApprovalSerializer(serializers.Serializer):
    """Serializer for approving or rejecting orders"""
    approved = serializers.BooleanField()
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if not data.get('approved') and not data.get('rejection_reason'):
            raise serializers.ValidationError({"rejection_reason": "Reason is required when rejecting an order."})
        return data


class OrderBookSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = OrderBook
        fields = [
            'id',
            'product',
            'product_name',
            'timestamp',
            'best_bid',
            'best_ask',
            'total_bid_quantity',
            'total_ask_quantity',
            'bid_levels',
            'ask_levels'
        ]


class PriceHistorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = PriceHistory
        fields = [
            'id',
            'product',
            'product_name',
            'timestamp',
            'open_price',
            'high_price',
            'low_price',
            'close_price',
            'volume'
        ]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id',
            'user',
            'notification_type',
            'message',
            'related_order',
            'created_at',
            'read'
        ]
        read_only_fields = ['user', 'notification_type', 'message', 'related_order', 'created_at']
