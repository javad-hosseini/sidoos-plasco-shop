from django.urls import path, register_converter
from . import views
from .converters import UnicodeSlugConverter

register_converter(UnicodeSlugConverter, 'unicode_slug')

app_name = 'products'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('special-sales/', views.special_sales, name='special_sales'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/<slug:slug>/', views.category_products, name='category_products'),
    path('api/<int:product_id>/save/', views.toggle_save, name='toggle_save'),
    path('api/<int:product_id>/like/', views.toggle_like, name='toggle_like'),
    path('<unicode_slug:slug>/', views.product_detail, name='product_detail'),
]