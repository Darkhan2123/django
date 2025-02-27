from django.db import models
from django.conf import settings
from products.models import Product

class RevenueReport(models.Model):
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='daily')
    start_date = models.DateField()              # start of the period (for daily, this is the date)
    end_date = models.DateField(null=True, blank=True)   # end of period (same as start_date for daily periods)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2)  # aggregated revenue in this period

    class Meta:
        unique_together = ('period_type', 'start_date', 'end_date')
        ordering = ['-start_date']

    def __str__(self):
        # If end_date is not set (daily period), use start_date as end
        end = self.end_date or self.start_date
        return f"{self.period_type.capitalize()} Revenue from {self.start_date} to {end}: {self.total_revenue}"

class TopProductReport(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    period_start = models.DateField()            # start of the period (e.g. day or week start)
    period_end = models.DateField(null=True, blank=True)    # end of the period (null for single-day periods)
    total_quantity = models.PositiveIntegerField()          # total units of the product sold in this period
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2)  # total revenue from this product in the period

    class Meta:
        unique_together = ('product', 'period_start', 'period_end')
        ordering = ['-total_quantity']

    def __str__(self):
        end = self.period_end or self.period_start
        period = f"{self.period_start} to {end}" if self.period_end else str(self.period_start)
        return f"TopProductReport({self.product.name}, {period})"
