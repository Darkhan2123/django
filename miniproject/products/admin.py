from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, Tag, ProductImage, StockUpdate


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_count')
    search_fields = ('name',)

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = "Number of Products"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "product_count", "description")
    search_fields = ("name",)

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = "Number of Products"


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'image_preview')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return "No Image"

    image_preview.short_description = "Preview"


class StockUpdateInline(admin.TabularInline):
    model = StockUpdate
    extra = 0
    fields = ('update_type', 'quantity', 'notes', 'updated_by', 'created_at')
    readonly_fields = ('created_at',)
    max_num = 5
    can_delete = False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sku",
        "category",
        "price",
        "quantity_in_stock",
        "status",
        "is_tradeable",
        "image_preview"
    )
    list_filter = ("category", "status", "is_tradeable", "created_at", "tags")
    search_fields = ("name", "sku", "description", "category__name")
    readonly_fields = ("created_at", "updated_at", "image_preview")
    autocomplete_fields = ("category", "tags")
    filter_horizontal = ("tags",)
    inlines = [ProductImageInline, StockUpdateInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'sku', 'category', 'tags')
        }),
        ('Details', {
            'fields': ('price', 'description', 'image', 'image_preview')
        }),
        ('Inventory', {
            'fields': ('quantity_in_stock', 'reorder_threshold', 'status', 'is_tradeable')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return "No Image"

    image_preview.short_description = "Image Preview"

    def save_model(self, request, obj, form, change):
        """When quantity is updated, check if stock update needed"""
        if change and 'quantity_in_stock' in form.changed_data:
            # Get the old instance from the database
            old_instance = self.model.objects.get(pk=obj.pk)
            old_quantity = old_instance.quantity_in_stock
            new_quantity = obj.quantity_in_stock
            quantity_diff = new_quantity - old_quantity

            # Create a stock update record
            if quantity_diff != 0:
                update_type = 'add' if quantity_diff > 0 else 'remove'
                StockUpdate.objects.create(
                    product=obj,
                    quantity=abs(quantity_diff),
                    update_type=update_type,
                    notes=f"Updated via admin panel by {request.user.username}",
                    updated_by=request.user
                )

        super().save_model(request, obj, form, change)


@admin.register(StockUpdate)
class StockUpdateAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "update_type",
        "quantity",
        "updated_by",
        "created_at"
    )
    list_filter = ("update_type", "created_at", "updated_by")
    search_fields = ("product__name", "product__sku", "notes")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("product", "updated_by")
    date_hierarchy = "created_at"

    def has_change_permission(self, request, obj=None):
        """Stock updates should not be modified after creation"""
        return False
