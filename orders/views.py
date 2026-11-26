from django.db.models import Q
from django.shortcuts import render
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView, RetrieveAPIView
from inventory.models import Product, StockMovement
from .models import Order, OrderItem
from .serializers import OrderCreateSerializer, OrderReadSerializer,OrderFilterSerializer
from inventory.permissions import IsOwnerOrReadOnly
from .pagination import OrderPagination
import logging
# Create your views here.
logger = logging.getLogger(__name__)
 
        
class OrderCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        with transaction.atomic():

            # 1. Retrieve and lock the order
            try:
                order = Order.objects.select_for_update().get(pk=pk)
            except Order.DoesNotExist:
                logger.warning("order %s is not found",
                                pk)
                return Response(
                    {"error": "Order not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
            if request.user != order.created_by and request.user.role != "OWNER":
                logger.warning(
                               "Unauthorized cancellation attempt on order %s by user %s",
                               order.id,
                               request.user.id)

                return Response(
                                 {"error": "Only the staff who created the order or an owner can cancel the order."},
                                 status=status.HTTP_403_FORBIDDEN)

            # 2. Check whether cancellation is allowed
            if order.status != Order.Status.PENDING:
                logger.warning(
                             "Cancellation rejected for order %s by user %s. Current status: %s",
                              order.id,
                              request.user.id,
                              order.status
    )        

                return Response(
                    {"error": "Only pending orders can be cancelled."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 3. Retrieve order items
            order_items = order.items.order_by("product_id")

            # 4. Restore stock for every product
            for item in order_items:
                product = Product.objects.select_for_update().get(
                    pk=item.product_id
                )

                product.stock_quantity += item.quantity

                product.save(
                    update_fields=["stock_quantity", "updated_at"]
                )

                # 5. Record the stock restoration
                StockMovement.objects.create(
                    product=product,
                    movement_type="CANCELLATION",
                    quantity_change=item.quantity,
                    quantity_after=product.stock_quantity,
                    created_by=request.user,
                    reason=f"Stock restored for Order #{order.id}"
                )

            # 6. Mark the order as cancelled
            order.status = Order.Status.CANCELLED

            order.save(
                update_fields=["status", "updated_at"]
            )
        logger.info(
               "Order %s cancelled successfully by user %s",
                order.id,
                request.user.id
)

        # 7. Return the response after the transaction
        return Response(
            {
                "message": "Order cancelled successfully.",
                "order_id": order.id,
                "status": order.status,
            },
            status=status.HTTP_200_OK
        )
 
class OrderDetailView(RetrieveAPIView):
    serializer_class = OrderReadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Order.objects.select_related(
        "created_by"
    ).prefetch_related(
        "items"
    )

        

        if self.request.user.role == "OWNER":
            print("OWNER: returning all orders")
            return queryset
        return queryset.filter(created_by=self.request.user)

class OrderView(ListAPIView):
    serializer_class = OrderReadSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OrderPagination
    def get_queryset(self):
        queryset = Order.objects.select_related(
        "created_by"
    ).prefetch_related(
        "items"
    )

        if self.request.user.role != "OWNER":
            queryset = queryset.filter(created_by=self.request.user)

        order_filter = OrderFilterSerializer(
            data=self.request.query_params
    )
        order_filter.is_valid(raise_exception=True)
        search_term = order_filter.validated_data.get("search")
        status_value = order_filter.validated_data.get("status")
        created_after = order_filter.validated_data.get("created_after")
        created_before = order_filter.validated_data.get("created_before")
        if search_term:
            queryset = queryset.filter(
        Q(created_by__username__icontains=search_term) |
        Q(items__product_name__icontains=search_term)
    ).distinct()
        if status_value:
            queryset = queryset.filter(status=status_value)

        if created_after:
            queryset = queryset.filter(created_at__date__gte=created_after)

        if created_before:
            queryset = queryset.filter(created_at__date__lte=created_before)
        ordering = order_filter.validated_data.get("ordering")

        if ordering:
            queryset = queryset.order_by(ordering,"id")
        else:
            queryset = queryset.order_by("-created_at", "-id")
        return queryset
    def post(self, request):
            serializer = OrderCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
    
            items = serializer.validated_data["items"]
            with transaction.atomic():
                products = {}
    
                # First loop: retrieve products and check stock
                for item in sorted(items, key=lambda x: x["product"]):
                    product = Product.objects.select_for_update().get(
                        id=item["product"]
                    )
    
                    if product.stock_quantity < item["quantity"]:
                        logger.warning(
                                     "Order attempt rejected: insufficient stock for product %s by user %s. Requested: %s, Available: %s",
                                      product.id,
                                      request.user.id,
                                      item["quantity"],
                                      product.stock_quantity
    )
                        
                        return Response(
                            {
                                "error": f"Not enough stock for {product.name}"
                            },
                            status=status.HTTP_400_BAD_REQUEST
                        )
    
                    products[product.id] = product
    
                # Create the parent Order
                order = Order.objects.create(
                    created_by=request.user
                )
                total_price=0
                # Second loop: create items and deduct stock
                for item in items:
                    product = products[item["product"]]
                    quantity = item["quantity"]
                    total_price += quantity * product.price
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,
                        quantity=quantity,
                        unit_price=product.price
                    )
    
                    product.stock_quantity -= quantity
    
                    product.save(
                        update_fields=["stock_quantity", "updated_at"]
                    )
    
                    StockMovement.objects.create(
                        product=product,
                        movement_type="ORDER",
                        quantity_change=-quantity,
                        quantity_after=product.stock_quantity,
                        created_by=request.user,
                        reason=f"Stock deducted for Order #{order.id}"
                    )
            order.total_price = total_price
            order.save(update_fields=["total_price"])
            logger.info("Order %s created successfully by user %s. Total: %s",
                         order.id,
                         request.user.id,
                         order.total_price
)
            return Response(
                {
                    "message": "Order created successfully",
                    "order_id": order.id,
                    "status": order.status,
                    "total_price": order.total_price
                },
                status=status.HTTP_201_CREATED
            )
class ConfirmOrderView(APIView):
     permission_classes = [IsOwnerOrReadOnly,IsAuthenticated]

     def post(self, request, pk):
        with transaction.atomic():
            try:
                order = Order.objects.select_for_update().get(pk=pk)
            except Order.DoesNotExist:
                logger.warning(
                                "Confirmation attempt for nonexistent order %s by user %s",
                                  pk,
                                  request.user.id)

                return Response(
                    {"error": "Order not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

            if order.status != Order.Status.PENDING:
                logger.warning(
                               "Confirmation rejected for order %s by user %s. Current status: %s",
                                order.id,
                                request.user.id,
                                order.status)

                return Response(
                    {"error": "Only pending orders can be confirmed."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            order.status = Order.Status.CONFIRMED
            order.save(update_fields=["status", "updated_at"])
        logger.info(
            "Order %s confirmed successfully by user %s",
            order.id,
            request.user.id
        )

        return Response(
            {
                "message": "Order confirmed successfully.",
                "order_id": order.id,
                "status": order.status,
            },
            status=status.HTTP_200_OK
        )
    
     