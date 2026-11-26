from rest_framework import serializers
from .models import Category,Product,StockMovement
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
       model = Category
       fields = "__all__"
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model=Product
        fields= "__all__"
        read_only_fields = (
            "id",
            "stock_quantity",
            "created_at",
            "updated_at",
        )
class RestockSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
    reason = serializers.CharField()
class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = "__all__"
        