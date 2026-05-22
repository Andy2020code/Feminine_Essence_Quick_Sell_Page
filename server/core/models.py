from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='products/')
    badge = models.CharField(max_length=30, blank=True)  # "Mais Vendido", "Novo", etc.
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name