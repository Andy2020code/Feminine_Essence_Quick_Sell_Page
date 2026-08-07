from decimal import Decimal
from .models import Cart, CartItem, Product, CosmeticProduct

MODEL_MAP = {
    "Product": Product,
    "CosmeticProduct": CosmeticProduct,
}


class CartService:
    def __init__(self, request):
        self.user = request.user
        self.session = request.session

        if self.user.is_authenticated:
            self.cart, _ = Cart.objects.get_or_create(user=self.user)
        else:
            self.cart = None

    def add(self, obj, qty=1):
        item, created = CartItem.objects.get_or_create(
            cart=self.cart,
            product_type=obj.__class__.__name__,
            product_id=obj.id,
            defaults={
                "name": obj.name,
                "price": obj.price,
                "quantity": qty,
            }
        )

        if not created:
            item.quantity += qty
            item.save()

    def remove(self, obj):
        CartItem.objects.filter(
            cart=self.cart,
            product_type=obj.__class__.__name__,
            product_id=obj.id,
        ).delete()

    def clear(self):
        self.cart.items.all().delete()

    def items(self):
        enriched = []

        for item in self.cart.items.all():
            model = MODEL_MAP.get(item.product_type)
            if not model:
                continue

            product = model.objects.get(id=item.product_id)

            enriched.append({
                "item": item,
                "product": product,
                "quantity": item.quantity,
                "product_type": item.product_type,
                "product_id": item.product_id,
                "image": product.image.url if product.image else None,
            })

        return enriched

    def get_subtotal(self):
        return sum(item.price * item.quantity for item in self.cart.items.all())

    def get_discount(self):
        return Decimal("0.00")

    def get_delivery_fee(self):
        return Decimal("25.99")

    def get_sales_tax(self):
        return Decimal("5.99")

    def total(self):
        total = (
            sum(item.price * item.quantity for item in self.cart.items.all())
            + self.get_delivery_fee()
            + self.get_sales_tax()
            - self.get_discount()
        )

        return max(0, total)