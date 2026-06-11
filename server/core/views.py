import os
from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.db import transaction
from .models import Product, CosmeticProduct, Badge, CosmeticBadge, Order
from square import Square
from square.environment import SquareEnvironment
from decimal import Decimal
import time
import uuid
import json
import base64
import hmac
import hashlib
load_dotenv()

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
    badges = CosmeticBadge.objects.all()

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

@transaction.atomic
def square_checkout(request, product_type, product_id):

    if product_type == "lingerie":
        product = get_object_or_404(Product.objects.select_for_update(), id=product_id)
    elif product_type == "service":
        product = get_object_or_404(CosmeticProduct.objects.select_for_update(), id=product_id)
    else:
        return JsonResponse({"error": "Invalid product type"}, status=400)
    if product.stock <= 0:
        return JsonResponse({"error": "This item is out of stock"}, status=400)
    
    order = Order.objects.create(
        product_type=product_type,
        product_id=product.id,
        product_name=product.name,
        quantity=1,
        amount=product.price,
        status="pending",
    )

    client = Square(
        token=settings.SQUARE_ACCESS_TOKEN,
        environment=SquareEnvironment.PRODUCTION
    )
    try:
        result = client.checkout.payment_links.create(
            idempotency_key=str(uuid.uuid4()),
            order={
                "location_id": settings.SQUARE_LOCATION_ID,
                "line_items": [

                    {
                        "name": product.name,
                        "quantity": "1",
                        "base_price_money": {
                            "amount": int(product.price * Decimal("100")),
                            "currency": "USD"
                        }
                    }
                ]
            },
            checkout_options={
                "redirect_url": f"https://feminineessencestore.com/order_confirmation/{order.id}/",
                "ask_for_shipping_address": True,
                "merchant_support_email": "orders@feminineessencestore.com",
            }
        )
        order.square_payment_link_id = result.payment_link.id
        order.square_order_id = result.payment_link.order_id
        order.save()

        return redirect(result.payment_link.url)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
    
@transaction.atomic
def mark_order_paid(order):
    if order.status == "paid":
        return

    if order.product_type == "lingerie":
        product = get_object_or_404(Product.objects.select_for_update(), id=order.product_id)
    else:
        product = get_object_or_404(CosmeticProduct.objects.select_for_update(), id=order.product_id)

    if product.stock < order.quantity:
        order.status = "cancelled"
        order.save()
        return

    product.stock -= order.quantity
    product.save()

    order.status = "paid"
    order.save()
    
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "order_confirmation.html", {
        "order": order
    })

@csrf_exempt
def square_webhook(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    if not verify_square_signature(request):
        return JsonResponse({"error": "Invalid signature"}, status=401)

    data = json.loads(request.body)
    event_type = data.get("type")

    if event_type in ["payment.created", "payment.updated"]:
        payment = data.get("data", {}).get("object", {}).get("payment", {})
        square_order_id = payment.get("order_id")
        status = payment.get("status")

        if status == "COMPLETED" and square_order_id:
            order = Order.objects.filter(square_order_id=square_order_id).first()

            if order:
                mark_order_paid(order)

    return JsonResponse({"success": True})

def verify_square_signature(request):
    square_signature = request.headers.get("x-square-hmacsha256-signature")

    if not square_signature:
        return False

    body = request.body.decode("utf-8")
    string_to_sign = settings.SQUARE_WEBHOOK_URL + body

    digest = hmac.new(
        settings.SQUARE_WEBHOOK_SIGNATURE_KEY.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256
    ).digest()
    calculated_signature = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(calculated_signature, square_signature)