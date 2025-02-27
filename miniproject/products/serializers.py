from rest_framework import serializers
from .models import Category, Product, Tag, ProductImage, StockUpdate


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'product_count']

    def get_product_count(self, obj):
        return obj.products.count()


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary']


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer for listing products (lighter version)"""
    category_name = serializers.StringRelatedField(source='category')
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'sku',
            'price',
            'category_name',
            'status',
            'status_display',
            'quantity_in_stock',
            'image',
            'is_tradeable',
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """Detailed product serializer with nested relations"""
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        queryset=Category.objects.all(),
        write_only=True,
        required=False,
    )
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        source='tags',
        queryset=Tag.objects.all(),
        many=True,
        write_only=True,
        required=False,
    )
    additional_images = ProductImageSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'sku',
            'price',
            'description',
            'image',
            'category',
            'category_id',
            'tags',
            'tag_ids',
            'status',
            'status_display',
            'quantity_in_stock',
            'reorder_threshold',
            'is_tradeable',
            'additional_images',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_sku(self, value):
        """Ensure SKU is unique when creating or updating"""
        instance = self.instance
        if instance and instance.sku == value:
            return value

        if Product.objects.filter(sku=value).exists():
            raise serializers.ValidationError("A product with this SKU already exists.")
        return value

    def validate_price(self, value):
        """Ensure price is positive"""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

    def create(self, validated_data):
        """Handle creation with related objects"""
        tags = validated_data.pop('tags', [])
        product = Product.objects.create(**validated_data)

        if tags:
            product.tags.set(tags)

        return product

    def update(self, instance, validated_data):
        """Handle updates with related objects"""
        tags = validated_data.pop('tags', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if tags is not None:
            instance.tags.set(tags)

        return instance


class StockUpdateSerializer(serializers.ModelSerializer):
    """Serializer for stock updates"""
    updated_by_username = serializers.StringRelatedField(source='updated_by.username', read_only=True)
    product_name = serializers.StringRelatedField(source='product.name', read_only=True)

    class Meta:
        model = StockUpdate
        fields = [
            'id',
            'product',
            'product_name',
            'quantity',
            'update_type',
            'notes',
            'updated_by',
            'updated_by_username',
            'created_at',
        ]
        read_only_fields = ['created_at', 'updated_by']

    def create(self, validated_data):
        """Create stock update and update the product quantity"""
        product = validated_data.get('product')
        quantity = validated_data.get('quantity')
        update_type = validated_data.get('update_type')

        # Set the requesting user
        validated_data['updated_by'] = self.context['request'].user

        # Create the stock update
        stock_update = StockUpdate.objects.create(**validated_data)

        # Update the product quantity
        if update_type == 'add':
            product.quantity_in_stock += quantity
        elif update_type == 'remove':
            product.quantity_in_stock = max(0, product.quantity_in_stock - quantity)
        elif update_type == 'adjust':
            product.quantity_in_stock = quantity

        product.save()

        return stock_update
