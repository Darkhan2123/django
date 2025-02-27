from django.contrib import admin
from .models import RevenueReport, TopProductReport

@admin.register(RevenueReport)
class RevenueReportAdmin(admin.ModelAdmin):
    list_display = ('period_type', 'start_date', 'end_date', 'total_revenue')
    list_filter = ('period_type',)
    search_fields = ('period_type',)
    date_hierarchy = 'start_date'  # enables quick navigation by date in admin

@admin.register(TopProductReport)
class TopProductReportAdmin(admin.ModelAdmin):
    list_display = ('product', 'period_start', 'period_end', 'total_quantity', 'total_revenue')
    list_filter = ('product',)
    search_fields = ('product__name',)
    date_hierarchy = 'period_start'
