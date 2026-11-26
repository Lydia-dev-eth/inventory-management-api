from django.test import TestCase

# Create your tests here.
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from inventory.models import Category, Product, StockMovement
from orders.models import Order, OrderItem


User = get_user_model()


class OrderCreationTests(APITestCase):

    def setUp(self):
        # Create a user
        self.user = User.objects.create_user(
            username="staff_test",
            password="testpassword123"
        )

        # Create a category
        self.category = Category.objects.create(
            name="Electronics"
        )

        # Create a product with 10 units
        self.product = Product.objects.create(
            name="Dell Laptop",
            code="DELL-001",
            category=self.category,
            price=Decimal("45000.00"),
            stock_quantity=10
        )

        # Authenticate the API client
        self.client.force_authenticate(user=self.user)

        self.url = "/api/orders/"

    def test_create_order_successfully(self):

        # Arrange: Prepare the request data
        data = {
            "items": [
                {
                    "product": self.product.id,
                    "quantity": 2
                }
            ]
        }

        # Act: Send the POST request
        response = self.client.post(
            self.url,
            data,
            format="json"
        )

        # Assert: Check the response
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        # Check that an Order was created
        self.assertEqual(Order.objects.count(), 1)

        # Check that an OrderItem was created
        self.assertEqual(OrderItem.objects.count(), 1)

        # Check that stock was deducted
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)

        # Check that stock movement was recorded
        self.assertEqual(StockMovement.objects.count(), 1)

        movement = StockMovement.objects.first()

        self.assertEqual(movement.movement_type, "ORDER")
        self.assertEqual(movement.quantity_change, -2)
        self.assertEqual(movement.quantity_after, 8)
    def test_order_fails_when_stock_is_insufficient(self):
        data = {
        "items": [
            {
                "product": self.product.id,
                "quantity": 15
            }
        ]
    }
        response = self.client.post(
        self.url,
        data,
        format="json"
    )
        self.assertEqual(
        response.status_code,
        status.HTTP_400_BAD_REQUEST
    )

        self.assertEqual(Order.objects.count(), 0)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)

        self.assertEqual(StockMovement.objects.count(), 0)
    def test_order_fails_for_inactive_product(self):
        self.product.is_active = False
        self.product.save()

        data = {
        "items": [
            {
                "product": self.product.id,
                "quantity": 2
            }
        ]
    }

        response = self.client.post(
        self.url,
        data,
        format="json"
    )

        self.assertEqual(
        response.status_code,
        status.HTTP_400_BAD_REQUEST
    )

        self.assertEqual(Order.objects.count(), 0)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)

        self.assertEqual(StockMovement.objects.count(), 0)
    def test_order_rejects_duplicate_products(self):
        data = {
        "items": [
            {"product": self.product.id, "quantity": 2},
            {"product": self.product.id, "quantity": 3}
        ]
    }

        response = self.client.post(
        self.url,
        data,
        format="json"
    )

        self.assertEqual(
        response.status_code,
        status.HTTP_400_BAD_REQUEST
    )

        self.assertEqual(Order.objects.count(), 0)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)

        self.assertEqual(StockMovement.objects.count(), 0)  
    def test_order_fails_for_nonexistent_product(self):
        data = {
        "items": [
            {
                "product": 9999,
                "quantity": 2
            }
        ]
    }

        response = self.client.post(
        self.url,
        data,
        format="json"
    )

        self.assertEqual(
        response.status_code,
        status.HTTP_400_BAD_REQUEST
    )

        self.assertEqual(Order.objects.count(), 0)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)

        self.assertEqual(StockMovement.objects.count(), 0)
    def test_unauthenticated_user_cannot_create_order(self):
        self.client.force_authenticate(user=None)

        data = {
        "items": [
            {
                "product": self.product.id,
                "quantity": 2
            }
        ]
    }

        response = self.client.post(
        self.url,
        data,
        format="json"
    )

        self.assertEqual(
        response.status_code,
        status.HTTP_401_UNAUTHORIZED
    )

        self.assertEqual(Order.objects.count(), 0)
    def test_order_preserves_product_details(self):
        data = {
        "items": [
            {
                "product": self.product.id,
                "quantity": 2
            }
        ]
    }

        response = self.client.post(
        self.url,
        data,
        format="json"
    )

        self.assertEqual(
        response.status_code,
        status.HTTP_201_CREATED
    )

        order_item = OrderItem.objects.get()

        # Change the original product details
        self.product.name = "Updated Laptop"
        self.product.price = Decimal("50000.00")
        self.product.save()

    # The old order must preserve its original details
        order_item.refresh_from_db()
 
        self.assertEqual(order_item.product_name, "Dell Laptop")
        self.assertEqual(order_item.unit_price, Decimal("45000.00"))
    def test_cancel_order_restores_stock(self):
    # Create an order for 3 laptops
        data = {
        "items": [
            {
                "product": self.product.id,
                "quantity": 3
            }
        ]
    }

        create_response = self.client.post(
        self.url,
        data,
        format="json"
    )

        order_id = create_response.data["order_id"]

    # Stock should now be 7
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 7)

    # Cancel the order
        cancel_response = self.client.post(
        f"{self.url}{order_id}/cancel/",
        format="json"
    )

        self.assertEqual(
        cancel_response.status_code,
        status.HTTP_200_OK
    )

    # Check that the order is cancelled
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.status, Order.Status.CANCELLED)

    # Check that stock returned to 10
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)

    # Check that cancellation movement was recorded
        cancellation_movement = StockMovement.objects.get(
        movement_type="CANCELLATION"
    )

        self.assertEqual(cancellation_movement.quantity_change, 3)
        self.assertEqual(cancellation_movement.quantity_after, 10)
    def test_order_cannot_be_cancelled_twice(self):
    # Create an order
         data = {
        "items": [
            {
                "product": self.product.id,
                "quantity": 3
            }
        ]
    }

         create_response = self.client.post(
        self.url,
        data,
        format="json"
    )

         order_id = create_response.data["order_id"]
         cancel_url = f"{self.url}{order_id}/cancel/"

    # First cancellation
         first_response = self.client.post(cancel_url)

         self.assertEqual(
        first_response.status_code,
        status.HTTP_200_OK
    )

    # Second cancellation
         second_response = self.client.post(cancel_url)

         self.assertEqual(
        second_response.status_code,
        status.HTTP_400_BAD_REQUEST
    )

    # Stock must remain 10
         self.product.refresh_from_db()
         self.assertEqual(self.product.stock_quantity, 10)

    # Only two movements should exist:
    # 1. ORDER
    # 2. CANCELLATION
         self.assertEqual(StockMovement.objects.count(), 2)
    def test_confirmed_order_cannot_be_cancelled(self):
    # Create an order
          data = {
        "items": [
            {
                "product": self.product.id,
                "quantity": 3
            }
        ]
    }

          create_response = self.client.post(
        self.url,
        data,
        format="json"
    )

          order_id = create_response.data["order_id"]

    # Change order status to CONFIRMED
          order = Order.objects.get(id=order_id)
          order.status = Order.Status.CONFIRMED
          order.save()

    # Try to cancel the confirmed order
          cancel_response = self.client.post(
        f"{self.url}{order_id}/cancel/"
    )

          self.assertEqual(
        cancel_response.status_code,
        status.HTTP_400_BAD_REQUEST
    )

    # Stock should remain 7
          self.product.refresh_from_db()
          self.assertEqual(self.product.stock_quantity, 7)

    # No cancellation movement should be created
          self.assertEqual(
        StockMovement.objects.filter(
            movement_type="CANCELLATION"
        ).count(),
        0
    )
    def test_cancel_nonexistent_order(self):
        response = self.client.post(
        "/api/orders/9999/cancel/"
    )

        self.assertEqual(
        response.status_code,
        status.HTTP_404_NOT_FOUND
    )

        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(StockMovement.objects.count(), 0)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)
    def test_unauthenticated_user_cannot_cancel_order(self):
    # Create an order while authenticated
        data = {
        "items": [
            {
                "product": self.product.id,
                "quantity": 3
            }
        ]
    }

        create_response = self.client.post(
        self.url,
        data,
        format="json"
    )

        order_id = create_response.data["order_id"]

    # Remove authentication
        self.client.force_authenticate(user=None)
 
    # Try to cancel without authentication
        response = self.client.post(
        f"{self.url}{order_id}/cancel/"
    )

        self.assertEqual(
        response.status_code,
        status.HTTP_401_UNAUTHORIZED
    )

    # Stock must remain 7
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 7)

    # Order must remain pending
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.status, Order.Status.PENDING)
    def test_cancel_order_with_multiple_products(self):
    # Create a second product
        mouse = Product.objects.create(
        name="Wireless Mouse",
        code="MOUSE-001",
        category=self.category,
        price=Decimal("1500.00"),
        stock_quantity=20
    )

    # Create an order with two products
        data = {
        "items": [
            {
                "product": self.product.id,
                "quantity": 3
            },
            {
                "product": mouse.id,
                "quantity": 2
            }
        ]
    }

        create_response = self.client.post(
        self.url,
        data,
        format="json"
    )

        self.assertEqual(
        create_response.status_code,
        status.HTTP_201_CREATED
    )

        order_id = create_response.data["order_id"]

    # Check stock after order creation
        self.product.refresh_from_db()
        mouse.refresh_from_db()

        self.assertEqual(self.product.stock_quantity, 7)
        self.assertEqual(mouse.stock_quantity, 18)

    # Cancel the order
        cancel_response = self.client.post(
        f"{self.url}{order_id}/cancel/"
    )

        self.assertEqual(
        cancel_response.status_code,
        status.HTTP_200_OK
    )

    # Check that BOTH products have their stock restored
        self.product.refresh_from_db()
        mouse.refresh_from_db()

        self.assertEqual(self.product.stock_quantity, 10)
        self.assertEqual(mouse.stock_quantity, 20)
    def test_staff_cannot_view_another_staffs_order(self):
        other_staff = User.objects.create_user(
        username="other_staff",
        password="testpassword123",
        role="STAFF"
    )
        other_order = Order.objects.create(
        created_by=other_staff
    )
        response = self.client.get(
        f"/api/orders/{other_order.id}/"
    )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    def test_owner_can_view_another_staffs_order(self):
        owner = User.objects.create_user(
        username="owner_test",
        password="testpassword123",
        role="OWNER"
    )
        self.assertEqual(owner.role, "OWNER")
        other_staff = User.objects.create_user(
        username="other_staff",
        password="testpassword123",
        role="STAFF"
    )
        other_order = Order.objects.create(
        created_by=other_staff
    )
        self.client.force_authenticate(user=owner)
        self.assertEqual(self.client.handler._force_user, owner)
        response = self.client.get(
        f"/api/orders/{other_order.id}/"
    )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], other_order.id)
    def test_staff_can_only_see_their_own_orders(self):
     other_staff = User.objects.create_user(
        username="other_staff",
        password="testpassword123",
        role="STAFF"
    )

     my_order = Order.objects.create(
        created_by=self.user
    )

     other_order = Order.objects.create(
        created_by=other_staff
    )
     response = self.client.get("/api/orders/")
      

     self.assertEqual(response.status_code, status.HTTP_200_OK)
     self.assertEqual(response.data["count"], 1)
     self.assertEqual(response.data["results"][0]["id"], my_order.id)
     self.assertNotEqual(response.data["results"][0]["id"], other_order.id)
    def test_owner_can_confirm_pending_order(self):
         owner = User.objects.create_user(
                username="owner_test",
                password="testpassword123",
                role="OWNER"
            )
         self.assertEqual(owner.role, "OWNER")
         other_staff = User.objects.create_user(
                 username="other_staff",
                 password="testpassword123",
                 role="STAFF"
             )
         other_order = Order.objects.create(
                 created_by=other_staff
             )
         self.client.force_authenticate(user=owner)
         response = self.client.post(
    f"/api/orders/{other_order.id}/confirm/"
)
         other_order.refresh_from_db()
         self.assertEqual(response.status_code, status.HTTP_200_OK)
         self.assertEqual(other_order.status, 'CONFIRMED')
    def test_stock_remain_same(self):
         data = {"items": [
                         {"product": self.product.id,
                             "quantity": 2}]}
         response = self.client.post(
                     self.url,
                     data,
                     format="json"
                 )
         self.assertEqual(response.status_code,status.HTTP_201_CREATED)
         self.product.refresh_from_db()
         stock_after_creation = self.product.stock_quantity
         order = Order.objects.get(pk=response.data["order_id"])
         response = self.client.post(
             f"/api/orders/{order.id}/confirm/"
         )
         self.product.refresh_from_db()
         self.assertEqual(self.product.stock_quantity, stock_after_creation)
    def test_staff_cannot_confirm(self):
        order = Order.objects.create(
                 created_by=self.user
             )
        response = self.client.post(
                     f"/api/orders/{order.id}/confirm/"
                 )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    def test_staff_cannot_cancel_another_staff_order(self):
     other_staff = User.objects.create_user(
        username="other_staff_cancel",
        password="testpassword123",
        role="STAFF"
    )

     order = Order.objects.create(
        created_by=other_staff
    )

     response = self.client.post(
        f"/api/orders/{order.id}/cancel/"
    )

     self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_cancel_another_staff_order(self):
     owner = User.objects.create_user(
        username="owner_cancel",
        password="testpassword123",
        role="OWNER"
    )

     

     order = Order.objects.create(
        created_by=self.user
    )

     self.client.force_authenticate(user=owner)

     response = self.client.post(
        f"/api/orders/{order.id}/cancel/"
    )

     order.refresh_from_db()

     self.assertEqual(response.status_code, status.HTTP_200_OK)
     self.assertEqual(order.status, Order.Status.CANCELLED)   
    def test_order_total_is_calculated_correctly(self):
     data = {
        "items": [
            {
                "product": self.product.id,
                "quantity": 2
            }
        ]
    }

     response = self.client.post(
        self.url,
        data,
        format="json"
    )

     self.assertEqual(response.status_code, status.HTTP_201_CREATED)

     order = Order.objects.get(pk=response.data["order_id"])

     expected_total = self.product.price * 2

     self.assertEqual(order.total_price, expected_total)
     self.assertEqual(response.data["total_price"], expected_total)     
    def test_order_detail_returns_total_price(self):
     data = {
        "items": [
            {
                "product": self.product.id,
                "quantity": 2
            }
        ]
    }

     response = self.client.post(
        self.url,
        data,
        format="json"
    )

     order_id = response.data["order_id"]

     detail_response = self.client.get(
        f"/api/orders/{order_id}/"
    )

     expected_total = self.product.price * 2

     self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
     self.assertEqual(
        detail_response.data["total_price"],
        str(expected_total)
    )
    def test_order_list_returns_total_price(self):
     data = {
        "items": [
            {
                "product": self.product.id,
                "quantity": 2
            }
        ]
    }

     create_response = self.client.post(
        self.url,
        data,
        format="json"
    )

     expected_total = self.product.price * 2

     list_response = self.client.get(self.url)

     self.assertEqual(list_response.status_code, status.HTTP_200_OK)

     order_data = next(
        order for order in list_response.data["results"]
        if order["id"] == create_response.data["order_id"]
    )

     self.assertEqual(order_data["total_price"], str(expected_total))
    def test_orders_are_paginated(self):
     for _ in range(11):
        Order.objects.create(created_by=self.user)

     response = self.client.get(self.url)

     self.assertEqual(response.status_code, status.HTTP_200_OK)
     self.assertEqual(response.data["count"], 11)
     self.assertEqual(len(response.data["results"]), 10)
     self.assertIsNotNone(response.data["next"])
     self.assertIsNone(response.data["previous"])
    def test_orders_second_page(self):
     for _ in range(11):
        Order.objects.create(created_by=self.user)

     response = self.client.get(f"{self.url}?page=2")

     self.assertEqual(response.status_code, status.HTTP_200_OK)
     self.assertEqual(len(response.data["results"]), 1)
     self.assertIsNone(response.data["next"])
     self.assertIsNotNone(response.data["previous"])
    def test_orders_second_page(self):
     for _ in range(11):
        Order.objects.create(created_by=self.user)

     response = self.client.get(f"{self.url}?page=2") 

     self.assertEqual(response.status_code, status.HTTP_200_OK)
     self.assertEqual(len(response.data["results"]), 1)
     self.assertIsNone(response.data["next"])
     self.assertIsNotNone(response.data["previous"])
    def test_staff_can_filter_orders_by_status(self):
       Order.objects.create(
        created_by=self.user,
        status=Order.Status.PENDING
    )
       Order.objects.create(
        created_by=self.user,
        status=Order.Status.CONFIRMED
    )
       Order.objects.create(
        created_by=self.user,
        status=Order.Status.CANCELLED
    )

       response = self.client.get(f"{self.url}?status=PENDING")

       self.assertEqual(response.status_code, status.HTTP_200_OK)
       self.assertEqual(response.data["count"], 1)
       self.assertEqual(response.data["results"][0]["status"], "PENDING")
    def test_staff_filter_does_not_show_other_staff_orders(self):
     other_staff = User.objects.create_user(
        username="other_staff",
        password="password123",
        role="STAFF"
    )

     Order.objects.create(
        created_by=self.user,
        status=Order.Status.PENDING
    )

     Order.objects.create(
        created_by=other_staff,
        status=Order.Status.PENDING
    )

     response = self.client.get(f"{self.url}?status=PENDING")

     self.assertEqual(response.status_code, status.HTTP_200_OK)
     self.assertEqual(response.data["count"], 1)
    def test_owner_can_filter_orders_by_status(self):
     owner = User.objects.create_user(
        username="owner",
        password="password123",
        role="OWNER"
    )

     other_staff = User.objects.create_user(
        username="other_staff",
        password="password123",
        role="STAFF"
    )

     Order.objects.create(
        created_by=self.user,
        status=Order.Status.PENDING
    )

     Order.objects.create(
        created_by=other_staff,
        status=Order.Status.PENDING
    )

     Order.objects.create(
        created_by=self.user,
        status=Order.Status.CONFIRMED
    )

     self.client.force_authenticate(user=owner)

     response = self.client.get(f"{self.url}?status=PENDING")

     self.assertEqual(response.status_code, status.HTTP_200_OK)
     self.assertEqual(response.data["count"], 2)
    def test_invalid_status_filter_returns_400(self):
       response = self.client.get(f"{self.url}?status=INVALID")

       self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    def test_filter_orders_created_after(self):
       order1 = Order.objects.create(created_by=self.user)
       order2 = Order.objects.create(created_by=self.user)
       order3 = Order.objects.create(created_by=self.user)

       Order.objects.filter(pk=order1.pk).update(
       created_at="2026-11-01 10:00:00+03:00"
    )
       Order.objects.filter(pk=order2.pk).update(
       created_at="2026-11-10 10:00:00+03:00"
    )
       Order.objects.filter(pk=order3.pk).update(
       created_at="2026-11-20 10:00:00+03:00"
    )

       response = self.client.get(
        f"{self.url}?created_after=2026-11-10"
    )

       self.assertEqual(response.status_code, status.HTTP_200_OK)
       self.assertEqual(response.data["count"], 2)
    def test_filter_orders_created_before(self):
     order1 = Order.objects.create(created_by=self.user)
     order2 = Order.objects.create(created_by=self.user)
     order3 = Order.objects.create(created_by=self.user)

     Order.objects.filter(pk=order1.pk).update(
        created_at="2026-11-01 10:00:00+03:00"
    )
     Order.objects.filter(pk=order2.pk).update(
        created_at="2026-11-10 10:00:00+03:00"
    )
     Order.objects.filter(pk=order3.pk).update(
        created_at="2026-11-20 10:00:00+03:00"
    )

     response = self.client.get(
        f"{self.url}?created_before=2026-11-10"
    )

     self.assertEqual(response.status_code, status.HTTP_200_OK)
     self.assertEqual(response.data["count"], 2)
    def test_filter_orders_by_date_range(self):
     order1 = Order.objects.create(created_by=self.user)
     order2 = Order.objects.create(created_by=self.user)
     order3 = Order.objects.create(created_by=self.user)
     order4 = Order.objects.create(created_by=self.user)

     Order.objects.filter(pk=order1.pk).update(
        created_at="2026-11-01 10:00:00+03:00"
    )
     Order.objects.filter(pk=order2.pk).update(
        created_at="2026-11-10 10:00:00+03:00"
    )
     Order.objects.filter(pk=order3.pk).update(
        created_at="2026-11-15 10:00:00+03:00"
    )
     Order.objects.filter(pk=order4.pk).update(
        created_at="2026-11-20 10:00:00+03:00"
    )

     response = self.client.get(
        f"{self.url}?created_after=2026-11-10&created_before=2026-11-15"
    )

     self.assertEqual(response.status_code, status.HTTP_200_OK)
     self.assertEqual(response.data["count"], 2)
    def test_invalid_date_filter_returns_400(self):
     response = self.client.get(
        f"{self.url}?created_after=not-a-date"
    )

     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    def test_invalid_date_range_returns_400(self):
     response = self.client.get(
        f"{self.url}?created_after=2026-11-20&created_before=2026-11-10"
    )

     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    def test_search_orders_by_product_name(self):
       order = Order.objects.create(created_by=self.user)

       OrderItem.objects.create(
        order=order,
        product=self.product,
        product_name=self.product.name,
        quantity=1,
        unit_price=self.product.price,
    )

       response = self.client.get(
        f"{self.url}?search={self.product.name}"
    )

       self.assertEqual(response.status_code, status.HTTP_200_OK)
       self.assertEqual(response.data["count"], 1)
    def test_search_orders_by_username(self):
     order = Order.objects.create(created_by=self.user)

     response = self.client.get(
        f"{self.url}?search={self.user.username}"
    )

     self.assertEqual(response.status_code, status.HTTP_200_OK)
     self.assertEqual(response.data["count"], 1)
    def test_staff_search_does_not_show_other_staff_orders(self):
       other_staff = User.objects.create_user(
        username="otherstaff",
        password="testpass123",
        role="STAFF",
    )

       order = Order.objects.create(created_by=other_staff)

       OrderItem.objects.create(
        order=order,
        product=self.product,
        product_name=self.product.name,
        quantity=1,
        unit_price=self.product.price,
    )

       response = self.client.get(
        f"{self.url}?search={self.product.name}"
    )

       self.assertEqual(response.status_code, status.HTTP_200_OK)
       self.assertEqual(response.data["count"], 0)
    def test_search_combines_with_status_and_date_filters(self):
       order1 = Order.objects.create(
        created_by=self.user,
        status=Order.Status.PENDING,
    )
       order2 = Order.objects.create(
        created_by=self.user,
        status=Order.Status.CONFIRMED,
    )
       order3 = Order.objects.create(
        created_by=self.user,
        status=Order.Status.PENDING,
    )

       for order in [order1, order2, order3]:
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            quantity=1,
            unit_price=self.product.price,
        )

       Order.objects.filter(pk=order1.pk).update(
       created_at="2026-11-01 10:00:00+03:00"
    )
       Order.objects.filter(pk=order2.pk).update(
        created_at="2026-11-15 10:00:00+03:00"
    )
       Order.objects.filter(pk=order3.pk).update(
        created_at="2026-11-20 10:00:00+03:00"
    )

       response = self.client.get(
        f"{self.url}?search={self.product.name}&status=PENDING&created_after=2026-11-10"
    )

       self.assertEqual(response.status_code, status.HTTP_200_OK)
       self.assertEqual(response.data["count"], 1)
    def test_orders_sorted_newest_first(self):
     order1 = Order.objects.create(created_by=self.user)
     order2 = Order.objects.create(created_by=self.user)
     order3 = Order.objects.create(created_by=self.user)

     Order.objects.filter(pk=order1.pk).update(
        created_at="2026-11-01 10:00:00+03:00"
    )
     Order.objects.filter(pk=order2.pk).update(
        created_at="2026-11-10 10:00:00+03:00"
    )
     Order.objects.filter(pk=order3.pk).update(
        created_at="2026-11-20 10:00:00+03:00"
    )

     response = self.client.get(
        f"{self.url}?ordering=-created_at"
    )

     self.assertEqual(response.status_code, status.HTTP_200_OK)

     returned_ids = [
        order["id"] for order in response.data["results"]
    ]

     self.assertEqual(
        returned_ids,
        [order3.id, order2.id, order1.id]
    )
    def test_orders_sorted_oldest_first(self):
     order1 = Order.objects.create(created_by=self.user)
     order2 = Order.objects.create(created_by=self.user)
     order3 = Order.objects.create(created_by=self.user)

     Order.objects.filter(pk=order1.pk).update(
        created_at="2026-11-01 10:00:00+03:00"
    )
     Order.objects.filter(pk=order2.pk).update(
        created_at="2026-11-10 10:00:00+03:00"
    )
     Order.objects.filter(pk=order3.pk).update(
        created_at="2026-11-20 10:00:00+03:00"
    )

     response = self.client.get(
        f"{self.url}?ordering=created_at"
    )

     self.assertEqual(response.status_code, status.HTTP_200_OK)

     returned_ids = [
        order["id"] for order in response.data["results"]
    ]

     self.assertEqual(
        returned_ids,
        [order1.id, order2.id, order3.id]
    )
    def test_orders_sorted_cheapest_first(self):
     order1 = Order.objects.create(
        created_by=self.user,
        total_price=500,
    )
     order2 = Order.objects.create(
        created_by=self.user,
        total_price=100,
    )
     order3 = Order.objects.create(
        created_by=self.user,
        total_price=300,
    )

     response = self.client.get(
        f"{self.url}?ordering=total_price"
    )

     self.assertEqual(response.status_code, status.HTTP_200_OK)

     returned_ids = [
        order["id"] for order in response.data["results"]
    ]

     self.assertEqual(
        returned_ids,
        [order2.id, order3.id, order1.id]
    )
    def test_orders_sorted_most_expensive_first(self):
     order1 = Order.objects.create(
        created_by=self.user,
        total_price=500,
    )
     order2 = Order.objects.create(
        created_by=self.user,
        total_price=100,
    )
     order3 = Order.objects.create(
        created_by=self.user,
        total_price=300,
    )

     response = self.client.get(
        f"{self.url}?ordering=-total_price"
    )

     self.assertEqual(response.status_code, status.HTTP_200_OK)

     returned_ids = [
        order["id"] for order in response.data["results"]
    ]

     self.assertEqual(
        returned_ids,
        [order1.id, order3.id, order2.id]
    )
    def test_invalid_ordering_returns_400(self):
     response = self.client.get(
        f"{self.url}?ordering=password"
    )

     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    def test_orders_are_newest_first_by_default(self):
     order1 = Order.objects.create(created_by=self.user)
     order2 = Order.objects.create(created_by=self.user)
     order3 = Order.objects.create(created_by=self.user)

     Order.objects.filter(pk=order1.pk).update(
        created_at="2026-11-01 10:00:00+03:00"
    )
     Order.objects.filter(pk=order2.pk).update(
        created_at="2026-11-10 10:00:00+03:00"
    )
     Order.objects.filter(pk=order3.pk).update(
        created_at="2026-11-20 10:00:00+03:00"
    )

     response = self.client.get(self.url)

     self.assertEqual(response.status_code, status.HTTP_200_OK)

     returned_ids = [
        order["id"] for order in response.data["results"]
    ]

     self.assertEqual(
        returned_ids,
        [order3.id, order2.id, order1.id]
    )