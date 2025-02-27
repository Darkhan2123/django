from django.shortcuts import render

# Create your views here.
from django.utils import timezone
from django.db.models import Q
from rest_framework import generics, viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Order, Transaction, OrderBook, PriceHistory, Notification
from .serializers import (
    OrderListSerializer,
    OrderDetailSerializer,
    TransactionSerializer,
    OrderApprovalSerializer,
    OrderBookSerializer,
    PriceHistorySerializer,
    NotificationSerializer
)
from .permissions import (
    IsTraderOrAdmin,
    IsOrderOwnerOrAdmin,
    CanApproveOrders,
    ReadOnly,
    CanViewTransactions
)
from .utils import attempt_to_match_order, update_order_book, check_expired_orders, cancel_all_user_orders


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing orders.
    """
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'order_type', 'status', 'time_in_force']
    search_fields = ['product__name', 'notes']
    ordering_fields = ['created_at', 'price', 'quantity']

    def get_queryset(self):
        """Filter orders based on user role"""
        if self.request.user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == 'list':
            return OrderListSerializer
        return OrderDetailSerializer

    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['create']:
            return [IsTraderOrAdmin()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsOrderOwnerOrAdmin()]
        elif self.action in ['approve']:
            return [CanApproveOrders()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        """Create a new order and try matching"""
        order = serializer.save()

        # If order is active, try to match it
        if order.status == 'active':
            attempt_to_match_order(order)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an order"""
        order = self.get_object()

        # Only cancel if the order is active, partially filled, or pending
        if order.status not in ['active', 'partially_filled', 'pending']:
            return Response(
                {"detail": f"Cannot cancel order with status '{order.status}'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '')
        if order.cancel(reason):
            # Create notification
            Notification.objects.create(
                user=order.user,
                notification_type='order_cancelled',
                message=f"Your {order.order_type} order for {order.product.name} was cancelled",
                related_order=order
            )

            return Response({"detail": "Order cancelled successfully"})

        return Response(
            {"detail": "Failed to cancel order"},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve or reject a pending order"""
        order = self.get_object()

        if order.status != 'pending':
            return Response(
                {"detail": "Only pending orders can be approved or rejected"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = OrderApprovalSerializer(data=request.data)
        if serializer.is_valid():
            approved = serializer.validated_data['approved']
            if approved:
                order.approve(request.user)

                # Create notification
                Notification.objects.create(
                    user=order.user,
                    notification_type='order_approved',
                    message=f"Your {order.order_type} order for {order.product.name} was approved",
                    related_order=order
                )

                # Try to match the order
                attempt_to_match_order(order)

                return Response({"detail": "Order approved successfully"})
            else:
                reason = serializer.validated_data.get('rejection_reason', '')
                order.reject(reason)

                # Create notification
                Notification.objects.create(
                    user=order.user,
                    notification_type='order_rejected',
                    message=f"Your {order.order_type} order for {order.product.name} was rejected: {reason}",
                    related_order=order
                )

                return Response({"detail": "Order rejected successfully"})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def cancel_all(self, request):
        """Cancel all active orders for the current user"""
        reason = request.data.get('reason', '')
        cancelled_count = cancel_all_user_orders(request.user, reason)

        return Response({
            "detail": f"Cancelled {cancelled_count} orders successfully"
        })

    @action(detail=False, methods=['get'])
    def pending_approval(self, request):
        """List orders pending approval (admin only)"""
        if not request.user.is_staff:
            return Response(
                {"detail": "You do not have permission to view pending orders"},
                status=status.HTTP_403_FORBIDDEN
            )

        orders = Order.objects.filter(status='pending')
        page = self.paginate_queryset(orders)

        if page is not None:
            serializer = OrderListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = OrderListSerializer(orders, many=True)
        return Response(serializer.data)


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing transactions.
    Read-only for all users, filtered by user's orders.
    """
    serializer_class = TransactionSerializer
    permission_classes = [CanViewTransactions]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['order__product', 'executed_at']
    ordering_fields = ['executed_at', 'executed_price']

    def get_queryset(self):
        if self.request.user.is_staff:
            return Transaction.objects.all()

        # Return transactions for orders owned by the user
        return Transaction.objects.filter(
            Q(order__user=self.request.user) |
            Q(counter_order__user=self.request.user)
        )


class OrderBookViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing order books.
    Read-only for all authenticated users.
    """
    queryset = OrderBook.objects.all()
    serializer_class = OrderBookSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product']
    ordering_fields = ['timestamp']

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get the latest order book for each product"""
        from django.db.models import Max

        # Get the latest timestamp for each product
        latest_timestamps = OrderBook.objects.values('product').annotate(
            latest_timestamp=Max('timestamp')
        )

        # Get the order books with these timestamps
        latest_books = []
        for item in latest_timestamps:
            order_book = OrderBook.objects.filter(
                product=item['product'],
                timestamp=item['latest_timestamp']
            ).first()

            if order_book:
                latest_books.append(order_book)

        serializer = OrderBookSerializer(latest_books, many=True)
        return Response(serializer.data)


class PriceHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing price history.
    Read-only for all authenticated users.
    """
    queryset = PriceHistory.objects.all()
    serializer_class = PriceHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product']
    ordering_fields = ['timestamp']

    @action(detail=False, methods=['get'])
    def product_history(self, request):
        """Get price history for a specific product"""
        product_id = request.query_params.get('product')
        if not product_id:
            return Response(
                {"detail": "Product ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get date range from query params
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')

        queryset = PriceHistory.objects.filter(product_id=product_id)

        if from_date:
            queryset = queryset.filter(timestamp__gte=from_date)
        if to_date:
            queryset = queryset.filter(timestamp__lte=to_date)

        queryset = queryset.order_by('timestamp')

        serializer = PriceHistorySerializer(queryset, many=True)
        return Response(serializer.data)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user notifications.
    Users can only view their own notifications.
    """
    serializer_class = NotificationSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def get_permissions(self):
        """Allow create for admin, read/update for user"""
        if self.action == 'create':
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        notification.read = True
        notification.save()
        return Response({"detail": "Notification marked as read"})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        return Response({"detail": "All notifications marked as read"})


class ExpireOrdersView(generics.GenericAPIView):
    """
    Admin-only view to manually check for and expire orders.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        """Check for expired orders and mark them as expired"""
        count = check_expired_orders()
        return Response({
            "detail": f"Checked for expired orders. {count} orders were expired."
        })
