from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import Product, Badge
import time

def landing(request):
    products = Product.objects.filter(is_active=True)
    return render(request, 'HOME.html', {'products': products})

def store_details(request):
    return render(request, 'store_details.html')

def lingerie_store(request):
    selected_badge = request.GET.get("badge")
    contents = Product.objects.all().order_by("-created_at")
    badges = Badge.objects.all()

    if selected_badge:
        contents = contents.filter(badges__name=selected_badge)

    return render(request, "lingerie_store.html", {
        "badges": badges,
        "selected_badge": selected_badge,
        "contents": contents,
        "css_version": int(time.time()),
    })

def product_details(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, "product_details.html", {
        "product": product,
    })

def contact_us(request):
    return render(request, 'contact_us.html')