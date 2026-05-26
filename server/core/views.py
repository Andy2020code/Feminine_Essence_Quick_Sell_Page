from django.shortcuts import render
from django.http import HttpResponse
from .models import Product

def landing(request):
    products = Product.objects.filter(is_active=True)
    return render(request, 'HOME.html', {'products': products})

def lingerie_store(request):
    return render(request, 'lingerie_store.html')

def product_details(request):
    return render(request, 'product_details.html')