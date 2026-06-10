from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('lingerie_store/', views.lingerie_store, name='lingerie_store'),
    path('product/<int:product_id>/', views.product_details, name='product_details'),
    path('cosmetic_store/', views.cosmetic_store, name='cosmetic_store'),
    path('cosmetic/<int:product_id>/', views.cosmetic_product_details, name='cosmetic_product_details'),
    path('store_details/', views.store_details, name='store_details'),
    path('contact_us/', views.contact_us, name='contact_us'),
    path("checkout/", views.square_checkout, name="square_checkout"),
]