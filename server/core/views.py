import os
from .models import Product, CosmeticProduct, Badge, CosmeticBadge, Order
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.http import HttpResponse, JsonResponse
from square.environment import SquareEnvironment
from django.contrib.auth import logout
from django.db import transaction
from django.conf import settings
from functools import lru_cache
from dotenv import load_dotenv
from decimal import Decimal
from square import Square
from .cart import CartService
import hashlib
import base64
import time
import uuid
import json
import hmac
load_dotenv()

def user_signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("user_login")
        else:
            print(form.errors)
    else:
        form = UserCreationForm()
    return render(request, "user_signup.html", {"form": form})

def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect("landing")

        return render(request, "user_login.html", {
            "error": "Invalid username or password."
        })
    return render(request, 'user_login.html')

def user_logout(request):

    logout(request)
    return redirect("user_login")

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
    else:
        contents = Product.objects.all()

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
    product_type = product.CART_TYPE
    return render(request, "product_details.html", {
        "product": product,
        "product_type": product_type,
        "qty_range": range(1, 10),
    })

def cosmetic_product_details(request, product_id):
    product = get_object_or_404(CosmeticProduct, id=product_id)
    product_type = product.CART_TYPE
    return render(request, "cosmetic_product_details.html", {
        "product": product,
        "product_type": product_type,
        "qty_range": range(1, 10),
    })

def contact_us(request):
    return render(request, 'contact_us.html')

@lru_cache
def get_square_client():

    env_map = {
        "sandbox": SquareEnvironment.SANDBOX,
        "production": SquareEnvironment.PRODUCTION,
    }

    return Square(
        token=settings.SQUARE_ACCESS_TOKEN,
        environment=env_map.get(
            settings.SQUARE_ENVIRONMENT,
            SquareEnvironment.SANDBOX
        )
    )

@login_required(login_url="user_login")
def cart_add(request, product_type, product_id):
    model = {
        "Product": Product,
        "CosmeticProduct": CosmeticProduct,
        "lingerie": Product,
    }.get(product_type)

    obj = get_object_or_404(model, id=product_id)
    cart = CartService(request)
    cart.add(obj)

    return redirect("cart_detail")

@login_required(login_url="user_login")
def cart_remove(request, product_type, product_id):
    model = {
        "Product": Product,
        "CosmeticProduct": CosmeticProduct,
        "lingerie": Product,
    }.get(product_type)

    obj = get_object_or_404(model, id=product_id)
    cart = CartService(request)
    cart.remove(obj)

    return redirect("cart_detail")

@login_required(login_url="user_login")
def cart_detail(request):
    cart = CartService(request)

    return render(request, "cart.html", {
        "items": cart.items(),
        "total": cart.total()
    })

@transaction.atomic
def square_checkout(request, product_type, product_id):

    try:
        item_quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        item_quantity = 1

    if product_type == "lingerie":
        product = get_object_or_404(
            Product.objects.select_for_update(),
            id=product_id
        )
    elif product_type == "service":
        product = get_object_or_404(
            CosmeticProduct.objects.select_for_update(),
            id=product_id
        )
    else:
        return JsonResponse({"error": "Invalid product type"}, status=400)

    # optional safety clamp
    if item_quantity < 1:
        item_quantity = 1

    if product.stock < item_quantity:
        return JsonResponse({"error": "Not enough stock"}, status=400)

    # create internal order
    order = Order.objects.create(
        status="pending",
        total_amount=product.price * item_quantity,
        user=request.user if request.user.is_authenticated else None,
    )

    client = get_square_client()

    try:
        result = client.checkout.payment_links.create(
            idempotency_key=str(uuid.uuid4()),
            order={
                "location_id": settings.SQUARE_LOCATION_ID,
                "line_items": [
                    {
                        "name": product.name,
                        "quantity": str(item_quantity),
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
def cart_checkout(request):
    cart = CartService(request)
    items = cart.items()

    if not items:
        return JsonResponse({"error": "Cart is empty"}, status=400)

    line_items = []

    for row in items:
        item = row["item"]
        product = row["product"]

        line_items.append({
            "name": product.name,
            "quantity": str(item.quantity),
            "base_price_money": {
                "amount": int(product.price * 100),
                "currency": "USD"
            }
        })

    # internal DB order (good)
    order = Order.objects.create(
        status="pending",
        total_amount=cart.total(),
        user=request.user if request.user.is_authenticated else None,
    )

    client = get_square_client()

    result = client.checkout.payment_links.create(
        idempotency_key=str(uuid.uuid4()),
        order={
            "location_id": settings.SQUARE_LOCATION_ID,
            "line_items": line_items
        },
        checkout_options={
            "redirect_url": f"https://feminineessencestore.com/order_confirmation/{order.id}/",
            "ask_for_shipping_address": True,
        }
    )

    order.square_payment_link_id = result.payment_link.id
    order.square_order_id = result.payment_link.order_id
    order.save()

    return redirect(result.payment_link.url)
    
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
    order = Order.objects.get(id=order_id)

    if order.status == "paid":
        CartService(request).clear()

    return render(request, "success.html", {"order": order})

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