from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

 
def __str__(self):
    return self.name
 

class Product(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, default="")

 
    category = models.ForeignKey(
    Category,
    on_delete=models.PROTECT,
    related_name="products",
)

    price = models.DecimalField(
    max_digits=10,
    decimal_places=2,
)

    stock_quantity = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.code})"
class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        RESTOCK = "RESTOCK", "Restock"
        ORDER = "ORDER", "Order"
        CANCELLATION = "CANCELLATION", "Cancellation"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    product = models.ForeignKey(
    Product,
    on_delete=models.PROTECT,
    related_name="stock_movements",
)

    movement_type = models.CharField(
    max_length=20,
    choices=MovementType.choices,
)

    quantity_change = models.IntegerField()

    quantity_after = models.PositiveIntegerField()

    created_by = models.ForeignKey(
    "accounts.User",
    on_delete=models.PROTECT,
    related_name="stock_movements",
)

    reason = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):return (
        f"{self.product.name}: "
        f"{self.quantity_change:+} "
        f"({self.movement_type})"
    )
 