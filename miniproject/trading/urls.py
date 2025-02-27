from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    OrderViewSet,
    TransactionViewSet,
    OrderBookViewSet,
    PriceHistoryViewSet,
    NotificationViewSet,
    ExpireOrdersView
)

app_name = 'trading'

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'order-books', OrderBookViewSet, basename='order-book')
router.register(r'price-history', PriceHistoryViewSet, basename='price-history')
router.register(r'notifications', NotificationViewSet, basename='notification')

# The API URLs are now determined automatically by the router
urlpatterns = [
    # Include the router-generated URLs
    path('', include(router.urls)),

    # Additional URLs that aren't handled by the router
    path('expire-orders/', ExpireOrdersView.as_view(), name='expire-orders'),
]
