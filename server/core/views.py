from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.db import transaction
from django.conf import settings
from django.urls import reverse
from square.environment import SquareEnvironment
from square import Square
from decimal import Decimal
from .models import Product, CosmeticProduct, Badge, CosmeticBadge, Order
from .cart import CartService
import hashlib
import logging
import base64
import time
import uuid
import json
import hmac

logger = logging.getLogger('csp.violations')
logger_sqreckout = logging.getLogger(__name__)
critical_logger = logging.getLogger('csp.critical')

def user_signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            logger.info("New user registered successfully")
            return redirect("user_login")
        logger.warning("User signup form invalid: %s", form.errors)
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
    if request.method != "POST":
        return redirect("landing")
    logout(request)
    return redirect("user_login")

def landing(request):
    products = Product.objects.filter(is_active=True)
    return render(request, 'HOME.html', {'products': products})

def store_details(request):
    return render(request, 'store_details.html')

def lingerie_store(request):
    selected_badge = request.GET.get("badge")
    badges = Badge.objects.all()

    qs = Product.objects.order_by("-created_at")

    if selected_badge:
        qs = qs.filter(badges__name=selected_badge).distinct()

    contents = qs[:10]

    return render(request, "lingerie_store.html", {
        "badges": badges,
        "selected_badge": selected_badge,
        "contents": contents,
        "css_version": int(time.time()),
    })

def cosmetic_store(request):
    selected_badge = request.GET.get("badge")
    badges = CosmeticBadge.objects.all()

    qs = CosmeticProduct.objects.order_by("-created_at")

    if selected_badge:
        qs = qs.filter(badges__name=selected_badge).distinct()

    contents = qs[:10]

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

def policy(request):
    return render(request, 'partials/policy.html')

_square_client = None
def get_square_client():
    global _square_client
    if _square_client is None:
        env_map = {
            "sandbox": SquareEnvironment.SANDBOX,
            "production": SquareEnvironment.PRODUCTION,
        }
        _square_client = Square(
            token=settings.SQUARE_ACCESS_TOKEN,
            environment=env_map.get(
                settings.SQUARE_ENVIRONMENT,
                SquareEnvironment.SANDBOX,
            ),
        )
    return _square_client

@login_required(login_url="user_login")
def cart_add(request, product_type, product_id):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    model_map = {
        "Product": Product,
        "CosmeticProduct": CosmeticProduct,
        "lingerie": Product,
    }
    model = model_map.get(product_type)
    if model is None:
        return JsonResponse({"error": "Invalid product type"}, status=400)

    obj = get_object_or_404(model, id=product_id)
    CartService(request).add(obj)
    return redirect("cart_detail")

@login_required(login_url="user_login")
def cart_remove(request, product_type, product_id):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    model_map = {
        "Product": Product,
        "CosmeticProduct": CosmeticProduct,
        "lingerie": Product,
    }
    model = model_map.get(product_type)
    if model is None:
        return JsonResponse({"error": "Invalid product type"}, status=400)

    obj = get_object_or_404(model, id=product_id)
    CartService(request).remove(obj)
    return redirect("cart_detail")

@login_required(login_url="user_login")
def cart_detail(request):
    cart = CartService(request)

    return render(request, "cart.html", {
        'items': cart.items(),
        'subtotal': cart.get_subtotal(),
        'discount': cart.get_discount(),
        'delivery': cart.get_delivery_fee(),
        'tax': cart.get_sales_tax(),
        'total': cart.total(),
    })

# In square_checkout, instantiate CartService with the request first,
# then call methods on that instance

@login_required(login_url="user_login")
def square_checkout(request, product_type, product_id):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        item_quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        item_quantity = 1

    item_quantity = max(1, item_quantity)      # clamp immediately

    if product_type == "lingerie":
        product = get_object_or_404(Product, id=product_id)
    elif product_type == "CosmeticProduct":
        product = get_object_or_404(CosmeticProduct, id=product_id)
    else:
        return JsonResponse({"error": "Invalid product type"}, status=400)

    # ✅ Instantiate with request — gives access to session/user context
    cart_service = CartService(request)

    subtotal     = Decimal(str(cart_service.get_subtotal()))    # instance call
    discount     = Decimal(str(cart_service.get_discount()))    # instance call
    delivery_fee = Decimal(str(cart_service.get_delivery_fee()))# instance call
    sales_tax    = Decimal(str(cart_service.get_sales_tax()))   # instance call

    total_amount = max(
        subtotal - discount + delivery_fee + sales_tax,
        Decimal("0.00"),
    )

    def _build_discount_part(discount: Decimal, to_cents) -> dict:
        if discount <= 0:
            return {}
        return {
            "discounts": [
                {
                    "uid": "discount-1",
                    "name": "Discontos",
                    "type": "FIXED_AMOUNT",
                    "amount_money": {
                        "amount": to_cents(discount),
                        "currency": "USD",
                    },
                    "scope": "ORDER",
                }
            ]
        }


    def _build_service_charge_part(
        delivery_fee: Decimal,
        sales_tax: Decimal,
        to_cents,
    ) -> dict:
        charges = []

        if delivery_fee > 0:
            charges.append({
                "uid": "delivery-1",
                "name": "Taxa de Entrega",
                "amount_money": {
                    "amount": to_cents(delivery_fee),
                    "currency": "USD",
                },
                "calculation_phase": "TOTAL_PHASE",
            })

        if sales_tax > 0:
            charges.append({
                "uid": "sales-fee-1",
                "name": "Taxa de Venda",
                "amount_money": {
                    "amount": to_cents(sales_tax),
                    "currency": "USD",
                },
                "calculation_phase": "TOTAL_PHASE",
            })

        return {"service_charges": charges} if charges else {}


    def to_cents(amount: Decimal) -> int:
        return int((amount * Decimal("100")).quantize(Decimal("1")))

    with transaction.atomic():
        product = product.__class__.objects.select_for_update().get(id=product_id)

        if product.stock < item_quantity:
            return JsonResponse({"error": "Not enough stock"}, status=400)

        order = Order.objects.create(
            status="pending",
            total_amount=total_amount,
            user=request.user,
            product_id=product_id,
            product_type=product_type,
            quantity=item_quantity,
        )

    try:
        result = get_square_client().checkout.payment_links.create(
            idempotency_key=str(uuid.uuid4()),
            order={
                "location_id": settings.SQUARE_LOCATION_ID,
                "line_items": [
                    {
                        "name": product.name,
                        "quantity": str(item_quantity),
                        "base_price_money": {
                            "amount": to_cents(product.price),
                            "currency": "USD",
                        },
                    }
                ],
                **_build_discount_part(discount, to_cents),
                **_build_service_charge_part(delivery_fee, sales_tax, to_cents),
            },
            checkout_options={
                "redirect_url": request.build_absolute_uri(
                    reverse("order_confirmation", args=[order.id])
                ),
                "ask_for_shipping_address": True,
                "merchant_support_email": "orders@feminineessencestore.com",
            },
        )
    except Exception:
        logger.exception("Square checkout failed for product %s", product_id)
        order.status = "cancelled"
        order.save()
        return JsonResponse(
            {"error": "Payment processing failed. Please try again."},
            status=502,
        )

    order.square_payment_link_id = result.payment_link.id
    order.square_order_id = result.payment_link.order_id
    order.save()

    return redirect(result.payment_link.url)
    
@login_required(login_url="user_login")
@transaction.atomic
def cart_checkout(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    cart = CartService(request)
    items = cart.items()

    if not items:
        return JsonResponse({"error": "Cart is empty"}, status=400)

    def to_cents(amount: Decimal) -> int:
        return int((Decimal(str(amount)) * Decimal("100")).quantize(Decimal("1")))

    line_items = [
        {
            "name": row["product"].name,
            "quantity": str(row["item"].quantity),
            "base_price_money": {
                "amount": to_cents(row["product"].price),
                "currency": "USD",
            },
        }
        for row in items
    ]

    subtotal     = Decimal(str(cart.get_subtotal()))
    discount     = Decimal(str(cart.get_discount()))
    delivery_fee = Decimal(str(cart.get_delivery_fee()))
    sales_tax    = Decimal(str(cart.get_sales_tax()))
    total_amount = max(
        subtotal - discount + delivery_fee + sales_tax,
        Decimal("0.00"),
    )

    with transaction.atomic():
        order = Order.objects.create(
            status="pending",
            total_amount=total_amount,
            user=request.user,
        )
    
    discount_part = {
        "discounts": [
            {
                "uid": "discount-1",
                "name": "Discontos",
                "type": "FIXED_AMOUNT",
                "amount_money": {
                    "amount": to_cents(discount),
                    "currency": "USD"
                },
                "scope": "ORDER"
            }
        ]
    } if discount > 0 else {}
    
    service_charges = []
    
    if delivery_fee > 0:
        service_charges.append({
            "uid": "delivery-1",
            "name": "Taxa de Entrega",
            "amount_money": {
                "amount": to_cents(delivery_fee),
                "currency": "USD"
            },
            "calculation_phase": "TOTAL_PHASE"
        })
    
    if sales_tax > 0:
        service_charges.append({
            "uid": "sales-fee-1",
            "name": "Taxa de Venda",
            "amount_money": {
                "amount": to_cents(sales_tax),
                "currency": "USD"
            },
            "calculation_phase": "TOTAL_PHASE"
        })
    
    service_charge_part = {
        "service_charges": service_charges
    } if service_charges else {}

    redirect_url = request.build_absolute_uri(reverse("order_confirmation", args=[order.id]))

    client = get_square_client()

    try:
        result = client.checkout.payment_links.create(
            idempotency_key=str(uuid.uuid4()),
            order={
                "location_id": settings.SQUARE_LOCATION_ID,
                "line_items": line_items,
                **discount_part,
                **service_charge_part,
            },
            checkout_options={
                "redirect_url": redirect_url,
                "ask_for_shipping_address": True,
            }
        )
    except Exception:
        logger.exception("Square cart checkout failed for user %s", request.user)
        order.status = "cancelled"
        order.save()
        return JsonResponse(
            {"error": "Payment processing failed. Please try again."},
            status=502
        )

    order.square_payment_link_id = result.payment_link.id
    order.square_order_id = result.payment_link.order_id
    order.save()

    return redirect(result.payment_link.url)
    
def mark_order_paid(order):
    if order.status == "paid":
        return

    # Cart-based orders don't track individual stock — handle separately
    if not order.product_id or not order.product_type:
        order.status = "paid"
        order.save()
        return

    if order.product_type == "lingerie":
        try:
            product = Product.objects.select_for_update().get(id=order.product_id)
        except Product.DoesNotExist:
            order.status = "cancelled"
            order.save()
            return
    else:
        try:
            product = CosmeticProduct.objects.select_for_update().get(id=order.product_id)
        except CosmeticProduct.DoesNotExist:
            order.status = "cancelled"
            order.save()
            return

    if product.stock < order.quantity:
        order.status = "cancelled"
        order.save()
        return

    product.stock -= order.quantity
    product.save()

    order.status = "paid"
    order.save()
    
def order_confirmation(request, order_id):
    if request.user.is_authenticated:
        order = get_object_or_404(Order, id=order_id, user=request.user)
    else:
        # For guest orders, scope by session or redirect to login
        return redirect("user_login")

    if order.status == "paid":
        CartService(request).clear()
        return render(request, "success.html", {"order": order})

    if order.status == "cancelled":
        return render(request, "order_cancelled.html", {"order": order})

    return render(request, "order_pending.html", {"order": order})

@csrf_exempt
def square_webhook(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    if not verify_square_signature(request):
        return JsonResponse({"error": "Invalid signature"}, status=401)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    event_type = data.get("type")

    if event_type in ["payment.created", "payment.updated"]:
        payment = (
            data.get("data", {})
                .get("object", {})
                .get("payment", {})
        )
        square_order_id = payment.get("order_id")
        status = payment.get("status")

    if status == "COMPLETED" and square_order_id:
        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(
                    square_order_id=square_order_id
                )
                mark_order_paid(order)
        except Order.DoesNotExist:
            logger.warning(
                "Webhook received for unknown order: %s", square_order_id
            )
        except Exception:
            logger.exception(
                "Failed to process webhook for order: %s", square_order_id
            )
            # Returning 500 causes Square to retry, potentially double-processing

    return JsonResponse({"success": True})

def verify_square_signature(request) -> bool:
    square_signature = request.headers.get("x-square-hmacsha256-signature", "")

    if not square_signature:
        return False

    try:
        body = request.body.decode("utf-8")
    except UnicodeDecodeError:
        return False

    string_to_sign = settings.SQUARE_WEBHOOK_URL + body

    mac = hmac.new(
        key=settings.SQUARE_WEBHOOK_SIGNATURE_KEY.encode("utf-8"),
        msg=string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    )
    calculated_signature = base64.b64encode(mac.digest()).decode("utf-8")

    return hmac.compare_digest(calculated_signature, square_signature)