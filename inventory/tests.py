from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from accounts.models import User
from inventory.models import Product, Category, StockMovement

# Create your tests here.
class ProductPermissionTests(APITestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="test_staff",
            password="testpassword123",
            role="STAFF",
        )
        self.owner_user = User.objects.create_user(
    username="test_owner",
    password="testpassword123",
    role="OWNER",
)
        self.category = Category.objects.create(name="Test Category")

        self.product = Product.objects.create(
            name="Test Product",
            code="TEST001",
            category=self.category,
            price=1000,
            stock_quantity=10,
        )
    def test_staff_cannot_update_product(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.patch(
            f"/api/inventory/products/{self.product.id}/",
            {"price": 2000},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    def test_owner_can_update_product(self):
        self.client.force_authenticate(user=self.owner_user)
        response = self.client.patch(
                    f"/api/inventory/products/{self.product.id}/",
                    {"price": 2000},
                    format="json",
                )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
    def test_staff_cannot_create_product(self):
     self.client.force_authenticate(user=self.staff_user)

     response = self.client.post(
        "/api/inventory/products/",
        {
            "name": "Unauthorized Product",
            "code": "UNAUTH001",
            "category": self.category.id,
            "price": 500,
        },
        format="json",
    )

     self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    def test_owner_can_create_product(self):
        self.client.force_authenticate(user=self.owner_user)
        response = self.client.post(
                "/api/inventory/products/",
                {
                    "name": "Unauthorized Product",
                    "code": "UNAUTH001",
                    "category": self.category.id,
                    "price": 500,
                },
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        def test_staff_can_restock_product(self):
         self.client.force_authenticate(user=self.staff_user)

         response = self.client.post(
            f"/api/inventory/products/{self.product.id}/stock-movements/",
            {
                "quantity": 5,
                "reason": "Test delivery",
            },
            format="json",
        )

         self.assertEqual(response.status_code, status.HTTP_200_OK)
         self.product.refresh_from_db()

         self.assertEqual(self.product.stock_quantity, 15)
         self.assertEqual(
            StockMovement.objects.filter(product=self.product).count(), 1
        )

        def test_anonymous_user_cannot_restock_product(self):
         response = self.client.post(
            f"/api/inventory/products/{self.product.id}/stock-movements/",
            {
                "quantity": 5,
                "reason": "Unauthorized delivery",
            },
            format="json",
        )

         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        def test_staff_can_view_stock_movements(self):
         self.client.force_authenticate(user=self.staff_user)

         response = self.client.get(
            f"/api/inventory/products/{self.product.id}/stock-movements/"
        )

         self.assertEqual(response.status_code, status.HTTP_200_OK)
        def test_staff_cannot_delete_category(self):
         self.client.force_authenticate(user=self.staff_user)

         response = self.client.delete(
            f"/api/inventory/categories/{self.category.id}/"
        )

         self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        def test_staff_cannot_create_category(self):
         self.client.force_authenticate(user=self.staff_user)

         response = self.client.post(
            "/api/inventory/categories/",
            {"name": "Unauthorized Category"},
            format="json",
        )

         self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        def test_staff_cannot_create_category(self):
         self.client.force_authenticate(user=self.staff_user)

         response = self.client.post(
            "/api/inventory/categories/",
            {"name": "Unauthorized Category"},
            format="json",
        )

         self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        def test_owner_can_delete_category(self):
         self.client.force_authenticate(user=self.owner_user)

         empty_category = Category.objects.create(
            name="Empty Category"
        )

         response = self.client.delete(
            f"/api/inventory/categories/{empty_category.id}/"
        )

         self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT
        )
        def test_staff_cannot_update_category(self):
         self.client.force_authenticate(user=self.staff_user)

         response = self.client.patch(
            f"/api/inventory/categories/{self.category.id}/",
            {"name": "Modified Category"},
            format="json",
        )

         self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN
        )
