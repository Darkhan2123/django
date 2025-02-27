from django.db import models
from django.core.validators import MinValueValidator


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('discontinued', 'Discontinued'),
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
    )

    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True, help_text="Stock Keeping Unit")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, related_name="products"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="product_images/", null=True, blank=True)
    quantity_in_stock = models.PositiveIntegerField(default=0)
    reorder_threshold = models.PositiveIntegerField(default=5, help_text="Reorder when stock falls below this level")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_tradeable = models.BooleanField(default=True, help_text="Whether this product can be traded")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Update status based on quantity
        if self.quantity_in_stock == 0:
            self.status = 'out_of_stock'
        elif self.quantity_in_stock <= self.reorder_threshold:
            self.status = 'low_stock'

        super().save(*args, **kwargs)

    @property
    def is_in_stock(self):
        return self.quantity_in_stock > 0


class ProductImage(models.Model):
    """Additional images for a product"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="additional_images")
    image = models.ImageField(upload_to="product_images/")
    alt_text = models.CharField(max_length=100, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"Image for {self.product.name}"


class StockUpdate(models.Model):
    """Track stock updates for products"""
    TYPE_CHOICES = (
        ('add', 'Stock Added'),
        ('remove', 'Stock Removed'),
        ('adjust', 'Stock Adjusted'),
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_updates")
    quantity = models.IntegerField(help_text="Positive for additions, negative for removals")
    update_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    notes = models.TextField(blank=True, null=True)
    updated_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.update_type.title()} - {self.product.name} - {self.quantity}"
