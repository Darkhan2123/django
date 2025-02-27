from django.shortcuts import render

# Create your views here.
from django.db.models import Sum, Count, Max, Min, Q, F
from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from .serializers import RevenueReportSerializer, TopProductReportSerializer
from .models import RevenueReport, TopProductReport
from trading.models import Order, Transaction

class RevenueReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to retrieve revenue reports. (Staff only)
    Supports filtering by period type (daily/weekly/monthly) and date range.
    """
    queryset = RevenueReport.objects.all()
    serializer_class = RevenueReportSerializer
    permission_classes = [permissions.IsAdminUser]

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        # Filter by period type if provided (daily, weekly, monthly)
        period_type = request.query_params.get('period_type')
        if period_type:
            queryset = queryset.filter(period_type=period_type)
        # Filter by date range (inclusive)
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            try:
                # Parse YYYY-MM-DD string to date
                from datetime import date
                start_date_obj = date.fromisoformat(start_date)
                queryset = queryset.filter(start_date__gte=start_date_obj)
            except ValueError:
                pass  # Ignore invalid date format
        if end_date:
            try:
                from datetime import date
                end_date_obj = date.fromisoformat(end_date)
                queryset = queryset.filter(end_date__lte=end_date_obj)
            except ValueError:
                pass
        queryset = queryset.order_by('start_date')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class TopProductReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to retrieve top-selling product metrics. (Staff only)
    Supports filtering by date range or specific product.
    By default, returns top products (sorted by quantity sold).
    """
    queryset = TopProductReport.objects.all()
    serializer_class = TopProductReportSerializer
    permission_classes = [permissions.IsAdminUser]

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        # Filter by specific product (to get stats for that product only)
        product_id = request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(product__id=product_id)
        # Filter by date range if provided
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            try:
                from datetime import date
                start_date_obj = date.fromisoformat(start_date)
                queryset = queryset.filter(period_start__gte=start_date_obj)
            except ValueError:
                pass
        if end_date:
            try:
                from datetime import date
                end_date_obj = date.fromisoformat(end_date)
                # For entries with period_end (e.g. weekly), use it; if no period_end (daily), use period_start
                queryset = queryset.filter(
                    Q(period_end__isnull=False, period_end__lte=end_date_obj) |
                    Q(period_end__isnull=True, period_start__lte=end_date_obj)
                )
            except ValueError:
                pass
        # Sort by quantity (and revenue as secondary) to get "top" products
        queryset = queryset.order_by('-total_quantity', '-total_revenue')
        # Limit the number of results to top N (default 5 if not specified and not filtering a single product)
        top_n_param = request.query_params.get('top_n')
        limit = 5  # default
        if top_n_param:
            try:
                limit = int(top_n_param)
            except ValueError:
                limit = 5
        if not product_id:  # only limit if viewing multiple products
            queryset = queryset[:limit]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class CustomerTrendsView(APIView):
    """
    API endpoint for customer order trends. (Staff only)
    Returns number of completed orders per customer, with first/last order dates and repeat-customer flag.
    Supports filtering by date range or specific customer.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, format=None):
        # Consider only completed orders (filled or partially_filled) for customer trend analysis
        orders = Order.objects.filter(status__in=['filled', 'partially_filled'])
        # Optional date range filter on order creation date
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            try:
                from datetime import date
                start_date_obj = date.fromisoformat(start_date)
                orders = orders.filter(created_at__date__gte=start_date_obj)
            except ValueError:
                pass
        if end_date:
            try:
                from datetime import date
                end_date_obj = date.fromisoformat(end_date)
                orders = orders.filter(created_at__date__lte=end_date_obj)
            except ValueError:
                pass
        # Optional filter by specific customer (user ID)
        customer_id = request.query_params.get('customer')
        if customer_id:
            orders = orders.filter(user__id=customer_id)
        # Aggregate order stats per customer
        stats = orders.values('user').annotate(
            username=F('user__username'),
            total_orders=Count('id'),
            first_order=Min('created_at'),
            last_order=Max('created_at')
        ).order_by('-total_orders')
        # Build response data
        data = []
        for entry in stats:
            data.append({
                'customer_id': entry['user'],
                'username': entry['username'],
                'total_orders': entry['total_orders'],
                'first_order_date': entry['first_order'],
                'last_order_date': entry['last_order'],
                'repeat_customer': entry['total_orders'] > 1  # True if more than one order
            })
        return Response(data)

class TopTradersView(APIView):
    """
    API endpoint for most active traders by number of executed orders. (Staff only)
    Supports filtering by date range or product.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, format=None):
        # Consider only executed orders (filled or partially_filled) for trader activity
        orders = Order.objects.filter(status__in=['filled', 'partially_filled'])
        # Date range filtering on order creation date
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            try:
                from datetime import date
                start_date_obj = date.fromisoformat(start_date)
                orders = orders.filter(created_at__date__gte=start_date_obj)
            except ValueError:
                pass
        if end_date:
            try:
                from datetime import date
                end_date_obj = date.fromisoformat(end_date)
                orders = orders.filter(created_at__date__lte=end_date_obj)
            except ValueError:
                pass
        # Optional filter by product (trades involving a specific product)
        product_id = request.query_params.get('product')
        if product_id:
            orders = orders.filter(product__id=product_id)
        # Aggregate trades count per user
        trader_stats = orders.values('user').annotate(
            username=F('user__username'),
            total_orders=Count('id')
        ).order_by('-total_orders')
        # Limit to top N traders (default 5)
        top_n_param = request.query_params.get('top_n')
        limit = 5
        if top_n_param:
            try:
                limit = int(top_n_param)
            except ValueError:
                limit = 5
        trader_stats = trader_stats[:limit]
        # Build response data
        data = []
        for entry in trader_stats:
            data.append({
                'trader_id': entry['user'],
                'username': entry['username'],
                'completed_orders': entry['total_orders']
            })
        return Response(data)

class TopTransactionsView(APIView):
    """
    API endpoint for highest-volume transactions. (Staff only)
    Returns top transactions by quantity (volume), with optional filtering by date range or product.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, format=None):
        transactions = Transaction.objects.all()
        # Optional date range filtering on transaction execution date
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            try:
                from datetime import date
                start_date_obj = date.fromisoformat(start_date)
                transactions = transactions.filter(executed_at__date__gte=start_date_obj)
            except ValueError:
                pass
        if end_date:
            try:
                from datetime import date
                end_date_obj = date.fromisoformat(end_date)
                transactions = transactions.filter(executed_at__date__lte=end_date_obj)
            except ValueError:
                pass
        # Optional filter by product (transactions for a specific product)
        product_id = request.query_params.get('product')
        if product_id:
            transactions = transactions.filter(order__product__id=product_id)
        # Sort by quantity descending to get highest volume trades
        transactions = transactions.order_by('-quantity')
        # Limit to top N transactions (default 5)
        top_n_param = request.query_params.get('top_n')
        limit = 5
        if top_n_param:
            try:
                limit = int(top_n_param)
            except ValueError:
                limit = 5
        transactions = transactions[:limit]
        # Build response data for each top transaction
        data = []
        for tx in transactions:
            data.append({
                'transaction_id': tx.id,
                'product': tx.order.product.name if tx.order and tx.order.product else None,
                'quantity': tx.quantity,
                'executed_price': tx.executed_price,
                'executed_at': tx.executed_at,
                'buyer': tx.order.user.username if tx.order else None,
                'seller': tx.counter_order.user.username if tx.counter_order else None
            })
        return Response(data)

class OrderStatusSummaryView(APIView):
    """
    API endpoint for order fulfillment rates and status distribution. (Staff only)
    Returns counts of orders by status and the fulfillment rate (percent of orders fully filled).
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, format=None):
        orders = Order.objects.all()
        # Optional filtering by order creation date range or product
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            try:
                from datetime import date
                start_date_obj = date.fromisoformat(start_date)
                orders = orders.filter(created_at__date__gte=start_date_obj)
            except ValueError:
                pass
        if end_date:
            try:
                from datetime import date
                end_date_obj = date.fromisoformat(end_date)
                orders = orders.filter(created_at__date__lte=end_date_obj)
            except ValueError:
                pass
        product_id = request.query_params.get('product')
        if product_id:
            orders = orders.filter(product__id=product_id)
        # Aggregate count of orders per status
        status_counts_query = orders.values('status').annotate(count=Count('id'))
        status_counts = {entry['status']: entry['count'] for entry in status_counts_query}
        total_orders = sum(status_counts.values())
        # Calculate fulfillment rate as percentage of orders that are completely filled
        filled_count = status_counts.get('filled', 0)
        fulfillment_rate = (filled_count / total_orders * 100) if total_orders > 0 else 0.0
        data = {
            'total_orders': total_orders,
            'status_counts': status_counts,
            'fulfillment_rate_percent': round(fulfillment_rate, 2)
        }
        return Response(data)
