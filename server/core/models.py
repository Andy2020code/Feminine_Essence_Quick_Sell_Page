from django.db import models
from django.conf import settings
from django import forms
from django.contrib.auth.models import User

class SignUpForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "email"]

    def clean(self):
        cleaned = super().clean()
        if cleaned["password1"] != cleaned["password2"]:
            raise forms.ValidationError("Passwords do not match")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save() 
        return user

class Badge(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    CART_TYPE = "lingerie"
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
    CART_TYPE = "cosmetic"
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    badges = models.ManyToManyField(CosmeticBadge, blank=True)  # "Mais Vendido", "Novo", etc.
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

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,       # <-- allows anonymous users
        blank=True,
    )

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    square_payment_link_id = models.CharField(max_length=100, blank=True)
    square_order_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} - {self.status}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")

    product_type = models.CharField(max_length=50)
    product_id = models.PositiveIntegerField()
    product_name = models.CharField(max_length=100)

    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product_type = models.CharField(max_length=50)
    product_id = models.PositiveIntegerField()
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def total_price(self):
        return self.price * self.quantity


class CSPViolation(models.Model):
    """Stores CSP violation reports for analysis."""

    DISPOSITION_CHOICES = [
        ('enforce', 'Enforce'),
        ('report', 'Report Only'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    document_uri = models.URLField(max_length=2000, blank=True)
    referrer = models.URLField(max_length=2000, blank=True)
    violated_directive = models.CharField(max_length=255, blank=True, db_index=True)
    effective_directive = models.CharField(max_length=255, blank=True, db_index=True)
    original_policy = models.TextField(blank=True)
    blocked_uri = models.CharField(max_length=2000, blank=True, db_index=True)
    source_file = models.CharField(max_length=2000, blank=True)
    line_number = models.IntegerField(default=0)
    column_number = models.IntegerField(default=0)
    status_code = models.IntegerField(default=0)
    script_sample = models.CharField(max_length=512, blank=True)
    disposition = models.CharField(
        max_length=50,
        choices=DISPOSITION_CHOICES,
        default='enforce'
    )

    class Meta:
        db_table = 'csp_violations'
        ordering = ['-timestamp']
        verbose_name = 'CSP Violation'
        verbose_name_plural = 'CSP Violations'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['effective_directive', '-timestamp']),
            models.Index(fields=['blocked_uri']),
            models.Index(fields=['disposition']),
        ]

    def __str__(self):
        return (
            f"[{self.timestamp:%Y-%m-%d %H:%M}] "
            f"{self.effective_directive} blocked {self.blocked_uri[:50]}"
        )

    @property
    def is_critical(self) -> bool:
        return self.effective_directive in {
            'script-src',
            'frame-ancestors',
            'form-action',
            'object-src',
        }