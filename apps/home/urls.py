from django.urls import path
from apps.home import views

app_name = 'home'

urlpatterns = [
    path('', views.home, name='home'),
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('price-lists/download/<int:pk>/', views.price_list_download, name='price_list_download'),
    path('price-lists/api/', views.price_list_api, name='price_list_api'),
]
