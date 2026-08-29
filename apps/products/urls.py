from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('special-sales/', views.special_sales, name='special_sales'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/new/', views.category_create, name='category_create'),
    path('categories/<slug:slug>/', views.category_products, name='category_products'),
    path('<slug:slug>/', views.product_detail, name='product_detail'),
]