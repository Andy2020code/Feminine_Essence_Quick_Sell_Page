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

    def total(self):
        total = 0

        for item in self.cart.items.all():
            model = MODEL_MAP.get(item.product_type)
            if not model:
                continue

            product = model.objects.get(id=item.product_id)
            total += product.price * item.quantity

        return total