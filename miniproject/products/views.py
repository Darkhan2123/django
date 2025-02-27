from rest_framework import generics, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, F

from .filters import ProductFilter

from .models import Category, Product, Tag, ProductImage, StockUpdate
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    TagSerializer,
    ProductImageSerializer,
    StockUpdateSerializer
)
from .permissions import IsAdminOrReadOnly, IsTraderOrAdminForTrading, IsSalesOrAdminForInventory


class CategoryViewSet(ModelViewSet):
    """
    ViewSet for listing, creating, retrieving, updating and deleting categories.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'products__count']

    def get_queryset(self):
        """Optionally annotate with product count"""
        queryset = Category.objects.all()

        if self.action == 'list':
            queryset = queryset.annotate(products__count=Count('products'))

        return queryset

    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """List all products in a category"""
        category = self.get_object()
        products = category.products.all()

        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)


class TagViewSet(ModelViewSet):
    """
    ViewSet for handling tags.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """List all products with this tag"""
        tag = self.get_object()
        products = tag.products.all()

        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)


class ProductViewSet(ModelViewSet):
    """
    ViewSet for handling products.
    """
    queryset = Product.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description', 'sku']
    ordering_fields = ['name', 'price', 'created_at', 'updated_at', 'quantity_in_stock']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductDetailSerializer

    def get_permissions(self):
        """
        Different permissions based on action:
        - list/retrieve: All authenticated users
        - create/update/delete: Admin only
        """
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    def get_queryset(self):
        """
        Filter queryset based on user role:
        - Admin: All products
        - Trader: Tradeable products
        - Sales: All products
        - Customer: Active products
        """
        queryset = Product.objects.all()

        if self.request.user.is_staff:
            return queryset

        user_role = getattr(self.request.user, 'role', None)

        if user_role == 'trader':
            return queryset.filter(is_tradeable=True)
        elif user_role == 'customer':
            return queryset.filter(status='active')

        return queryset

    @action(detail=True, methods=['post'], permission_classes=[IsSalesOrAdminForInventory])
    def add_stock(self, request, pk=None):
        """Add stock to a product"""
        product = self.get_object()

        serializer = StockUpdateSerializer(
            data={
                'product': product.id,
                'quantity': request.data.get('quantity', 0),
                'update_type': 'add',
                'notes': request.data.get('notes', '')
            },
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsSalesOrAdminForInventory])
    def remove_stock(self, request, pk=None):
        """Remove stock from a product"""
        product = self.get_object()

        serializer = StockUpdateSerializer(
            data={
                'product': product.id,
                'quantity': request.data.get('quantity', 0),
                'update_type': 'remove',
                'notes': request.data.get('notes', '')
            },
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def stock_history(self, request, pk=None):
        """Get stock update history for a product"""
        product = self.get_object()
        stock_updates = product.stock_updates.all()

        page = self.paginate_queryset(stock_updates)
        if page is not None:
            serializer = StockUpdateSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = StockUpdateSerializer(stock_updates, many=True)
        return Response(serializer.data)


class ProductImageViewSet(ModelViewSet):
    """
    ViewSet for handling additional product images.
    """
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        """Filter by product if provided"""
        queryset = ProductImage.objects.all()
        product_id = self.request.query_params.get('product')

        if product_id:
            queryset = queryset.filter(product_id=product_id)

        return queryset


class StockUpdateListView(generics.ListCreateAPIView):
    """
    List and create stock updates.
    Only admin and sales reps can access.
    """
    queryset = StockUpdate.objects.all()
    serializer_class = StockUpdateSerializer
    permission_classes = [IsSalesOrAdminForInventory]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'update_type', 'updated_by']
    search_fields = ['notes', 'product__name']
    ordering_fields = ['created_at', 'quantity']

    def perform_create(self, serializer):
        serializer.save(updated_by=self.request.user)
