from django.contrib import admin
from .models import Product, CosmeticProduct, Badge, CosmeticBadge


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


@admin.register(CosmeticProduct)
class CosmeticProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


@admin.register(CosmeticBadge)
class CosmeticBadgeAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
