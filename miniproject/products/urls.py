from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    TagViewSet,
    ProductViewSet,
    ProductImageViewSet,
    StockUpdateListView,
)

app_name = 'products'

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'', ProductViewSet, basename='product')
router.register(r'images', ProductImageViewSet, basename='product-image')

# Additional URLs that aren't handled by the router
urlpatterns = [
    path('stock-updates/', StockUpdateListView.as_view(), name='stock-update-list'),
    path('', include(router.urls)),
]
