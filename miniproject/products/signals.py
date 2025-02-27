from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.utils.text import slugify

from .models import Product, StockUpdate, Category


@receiver(post_save, sender=Product)
def update_product_cache(sender, instance, **kwargs):
    """
    Update cache when a product is saved
    """
    # Clear product cache
    cache_key = f'product_{instance.id}'
    cache.delete(cache_key)

    # Clear category product list cache
    if instance.category:
        cache_key = f'category_{instance.category.id}_products'
        cache.delete(cache_key)


@receiver(post_save, sender=StockUpdate)
def update_low_stock_notification(sender, instance, created, **kwargs):
    """
    Send notification for low stock when appropriate
    """
    if not created:
        return

    product = instance.product

    # Check if product is now low on stock or out of stock
    if product.status in ['low_stock', 'out_of_stock']:
        # In a real application, this would send an email or notification
        # to the appropriate users

        # For now, we'll just print a message
        print(f"ALERT: Product '{product.name}' is now {product.status}. Current stock: {product.quantity_in_stock}")


@receiver(post_save, sender=Category)
def update_category_cache(sender, instance, **kwargs):
    """
    Update cache when a category is saved
    """
    # Clear category cache
    cache_key = f'category_{instance.id}'
    cache.delete(cache_key)

    # Clear all categories list cache
    cache.delete('all_categories')
