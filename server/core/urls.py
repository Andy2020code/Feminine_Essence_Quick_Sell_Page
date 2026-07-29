from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('signup/', views.user_signup, name='user_signup'),
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('lingerie_store/', views.lingerie_store, name='lingerie_store'),
    path('product/<int:product_id>/', views.product_details, name='product_details'),
    path('cosmetic_store/', views.cosmetic_store, name='cosmetic_store'),
    path('cosmetic/<int:product_id>/', views.cosmetic_product_details, name='cosmetic_product_details'),
    path('store_details/', views.store_details, name='store_details'),
    path('contact_us/', views.contact_us, name='contact_us'),
    path('policy/', views.policy, name='policy_page'),
    path("cart/add/<str:product_type>/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/remove/<str:product_type>/<int:product_id>/", views.cart_remove, name="cart_remove"),
    path("cart_details/", views.cart_detail, name="cart_detail"),
    path("checkout/<str:product_type>/<int:product_id>/", views.square_checkout, name="square_checkout"),
    path("checkout/", views.cart_checkout, name="checkout"),
    path('order_confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path("square/webhook/", views.square_webhook, name="square_webhook"),
]