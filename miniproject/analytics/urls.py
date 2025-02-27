from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RevenueReportViewSet,
    TopProductReportViewSet,
    CustomerTrendsView,
    TopTradersView,
    TopTransactionsView,
    OrderStatusSummaryView
)

app_name = 'analytics'

router = DefaultRouter()
router.register(r'revenue-reports', RevenueReportViewSet, basename='revenue-report')
router.register(r'top-products', TopProductReportViewSet, basename='top-product-report')

urlpatterns = [
    # Router URLs for model-based reports
    path('', include(router.urls)),
    # Individual endpoints for dynamic analytics
    path('customer-trends/', CustomerTrendsView.as_view(), name='customer-trends'),
    path('trading-insights/top-traders/', TopTradersView.as_view(), name='top-traders'),
    path('trading-insights/top-transactions/', TopTransactionsView.as_view(), name='top-transactions'),
    path('order-status-summary/', OrderStatusSummaryView.as_view(), name='order-status-summary'),
]
