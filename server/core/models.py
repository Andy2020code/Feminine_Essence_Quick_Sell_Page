from django.db import models


class Badge(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    badges = models.ManyToManyField(Badge, blank=True)  # "Mais Vendido", "Novo", etc.
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    is_active = models.BooleanField(default=True)
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name
    

class CosmeticBadge(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class CosmeticProduct(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    badges = models.ManyToManyField(Badge, blank=True)  # "Mais Vendido", "Novo", etc.
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    is_active = models.BooleanField(default=True)
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name
    

class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("cancelled", "Cancelled"),
    ]

    product_type = models.CharField(max_length=50)
    product_id = models.PositiveIntegerField()
    product_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    customer_name = models.CharField(max_length=100, blank=True)
    customer_email = models.EmailField(blank=True)

    square_payment_link_id = models.CharField(max_length=100, blank=True)
    square_order_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)