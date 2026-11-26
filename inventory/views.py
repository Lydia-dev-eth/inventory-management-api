from django.shortcuts import render
from rest_framework import generics
from .models import Category,Product,StockMovement
from .serializers import CategorySerializer,ProductSerializer,RestockSerializer, StockMovementSerializer
from .permissions import IsOwnerOrReadOnly
from rest_framework.views import APIView, Response
from django.db import transaction
from rest_framework import status 
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
class CategoryListCreateView(generics.ListCreateAPIView):
    queryset=Category.objects.all()
    serializer_class=CategorySerializer
    permission_classes = [IsOwnerOrReadOnly]


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsOwnerOrReadOnly]

class ProductListCreateView(generics.ListCreateAPIView):
    queryset=Product.objects.all() 
    serializer_class= ProductSerializer
    permission_classes=[IsOwnerOrReadOnly]
class  ProductDetailView(generics.RetrieveUpdateAPIView):
    queryset=Product.objects.all()
    serializer_class=ProductSerializer
    permission_classes = [IsOwnerOrReadOnly]
class ProductStockMovementView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self,request,pk):
        serializer = RestockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data["quantity"]
        reason = serializer.validated_data["reason"]
        with transaction.atomic():
             product = get_object_or_404(
                Product.objects.select_for_update(),
                pk=pk
            )
             product.stock_quantity += quantity
             product.save(update_fields=["stock_quantity", "updated_at"])
             movement = StockMovement.objects.create(
                product=product,
                movement_type="RESTOCK",
                quantity_change=quantity,
                quantity_after=product.stock_quantity,
                created_by=request.user,
                reason=reason
            )
        return Response({
            "message": "Stock restocked successfully",
            "product_id": product.id,
            "product_name": product.name,
            "quantity_added": quantity,
            "current_stock": product.stock_quantity,
            "movement_id": movement.id
        }, status=status.HTTP_200_OK)
        
    def get(self, request, pk):
        movements = StockMovement.objects.filter(
            product_id=pk
        ).order_by("-created_at")

        serializer = StockMovementSerializer(
            movements,
            many=True
        )

        return Response(serializer.data)
             


