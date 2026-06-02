from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('lingerie_store/', views.lingerie_store, name='lingerie_store'),
    path('product/<int:product_id>/', views.product_details, name='product_details'),
    path('store_details/', views.store_details, name='store_details'),
    path('contact_us/', views.contact_us, name='contact_us'),
]