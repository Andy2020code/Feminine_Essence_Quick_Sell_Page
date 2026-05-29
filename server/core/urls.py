from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('lingerie_store/', views.lingerie_store, name='lingerie_store'),
    path('product/<int:product_id>/', views.product_details, name='product_details'),
]