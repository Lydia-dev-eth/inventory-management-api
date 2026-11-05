from django.contrib import admin
from .models import Category, Product, StockMovement


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "code",
        "category",
        "price",
        "stock_quantity",
        "is_active",
    )
    search_fields = ("name", "code")
    list_filter = ("category", "is_active")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "movement_type",
        "quantity_change",
        "quantity_after",
        "created_by",
        "created_at",
    )
    list_filter = ("movement_type", "created_at")
    search_fields = ("product__name", "product__code")
    readonly_fields = ("created_at",)