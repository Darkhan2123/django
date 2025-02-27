from rest_framework import serializers
from django.db import transaction
from .models import Invoice, SalesOrder, SalesOrderItem

class SalesOrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = SalesOrderItem
        fields = ["id", "product_id", "quantity", "price", "subtotal"]

class SalesOrderSerializer(serializers.ModelSerializer):
    items = SalesOrderItemSerializer(many=True, write_only=True)
    discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )

    class Meta:
        model = SalesOrder
        fields = [
            "id",
            "customer",
            "status",
            "discount_percent",
            "created_at",
            "items",
            "total",
        ]
        read_only_fields = ["customer", "total", "status", "created_at"]

    def validate_discount_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Discount percent must be between 0 and 100.")
        return value

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        # Wrap the creation in a transaction for data integrity.
        with transaction.atomic():
            sales_order = SalesOrder.objects.create(**validated_data)
            for item_data in items_data:
                SalesOrderItem.objects.create(
                    sales_order=sales_order,
                    product_id=item_data["product_id"],
                    quantity=item_data["quantity"],
                    price=item_data["price"],
                )
        return sales_order

class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ["id", "sales_order", "invoice_date"]
        read_only_fields = ["invoice_date"]
