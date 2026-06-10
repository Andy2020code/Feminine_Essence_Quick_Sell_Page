from django.contrib import admin
from .models import Product, CosmeticProduct, Badge, CosmeticBadge

admin.site.register(Product)
admin.site.register(CosmeticProduct)
admin.site.register(Badge)
admin.site.register(CosmeticBadge)
