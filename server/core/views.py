import os
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from .models import Product, CosmeticProduct, Badge
from square import Square
from square.environment import SquareEnvironment
import time
import uuid

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

def cosmetic_store(request):
    selected_badge = request.GET.get("badge")
    contents = CosmeticProduct.objects.all().order_by("-created_at")
    badges = Badge.objects.all()

    if selected_badge:
        contents = contents.filter(badges__name=selected_badge)

    return render(request, "cosmetic_store.html", {
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

def cosmetic_product_details(request, product_id):
    product = get_object_or_404(CosmeticProduct, id=product_id)
    return render(request, "cosmetic_product_details.html", {
        "product": product,
    })


def contact_us(request):
    return render(request, 'contact_us.html')

def square_checkout(request):

    client = Square(
        token=os.getenv("SQUARE_ACCESS_TOKEN"),
        environment=SquareEnvironment.SANDBOX
    )
    try:
        result = client.checkout.payment_links.create(
            idempotency_key=str(uuid.uuid4()),
            order={
                "location_id": os.getenv("SQUARE_LOCATION_ID"),
                "line_items": [

                    {
                        "name": "Feminine Essence Product",
                        "quantity": "1",
                        "base_price_money": {
                            "amount": 2500,
                            "currency": "USD"
                        }
                    }
                ]
            },
            checkout_options={

                "redirect_url": "http://127.0.0.1:8000/order-success/"
            }
        )
        return redirect(result.payment_link.url)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)