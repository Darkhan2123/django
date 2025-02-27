from rest_framework import serializers
from .models import RevenueReport, TopProductReport

class RevenueReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = RevenueReport
        fields = ['id', 'period_type', 'start_date', 'end_date', 'total_revenue']

class TopProductReportSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    class Meta:
        model = TopProductReport
        fields = ['id', 'product', 'product_name', 'period_start', 'period_end', 'total_quantity', 'total_revenue']
