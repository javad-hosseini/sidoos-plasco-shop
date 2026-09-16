from django.urls import path
from apps.home import views

app_name = 'home'

urlpatterns = [
    path('', views.home, name='home'),
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('price-lists/download/<int:pk>/', views.price_list_download, name='price_list_download'),
    path('price-lists/api/', views.price_list_api, name='price_list_api'),
    path('contact/', views.contact_us, name='contact'),
    path('guide/', views.purchase_guide, name='purchase_guide'),
    path('shipping/', views.shipping_terms, name='shipping_terms'),
    path('returns/', views.return_policy, name='return_policy'),
    path('faq/', views.faq, name='faq'),
]

