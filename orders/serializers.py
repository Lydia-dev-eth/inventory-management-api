from rest_framework import serializers

from django.db import models
from inventory.models import Product
from orders.models import Order, OrderItem


class OrderItemCreateSerializer(serializers.Serializer):
    product = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)
    def validate_product(self, value):
        if not Product.objects.filter(
            id=value,
            is_active=True
        ).exists():
            raise serializers.ValidationError(
                "Product does not exist or is inactive."
            )

        return value

class OrderCreateSerializer(serializers.Serializer):
    items = OrderItemCreateSerializer(many=True,  allow_empty=False)
    def validate_items(self, value):
        product_ids = [
            item["product"] for item in value
        ]

        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError(
                "A product can only appear once in an order."
            )

        return value
class OrderItemReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "quantity",
            "unit_price",
        ]
class OrderReadSerializer(serializers.ModelSerializer):
    items = OrderItemReadSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "created_by",
            "status",
            "total_price",
            "created_at",
            "updated_at",
            "items"
        ]
class OrderFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=Order.Status.choices,
        required=False
    )
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"
    created_after = serializers.DateField(required=False)
    created_before = serializers.DateField(required=False)
    search = serializers.CharField(required=False, allow_blank=True)
    def validate(self, data):
        created_after = data.get("created_after")
        created_before = data.get("created_before")

        if created_after and created_before:
         if created_after > created_before:
            raise serializers.ValidationError(
                "created_after cannot be later than created_before."
            )

        return data
    ordering = serializers.ChoiceField(
    choices=[
        "created_at",
        "-created_at",
        "total_price",
        "-total_price",
    ],
    required=False
)