# apps/accounts/urls.py
from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

app_name = 'accounts'

urlpatterns = [
    # Login/Logout using Django's built-in views
    path('login/', LoginView.as_view(
        template_name='accounts/login.html',
        redirect_authenticated_user=True,
    ), name='login'),

    path('logout/', LogoutView.as_view(
        next_page='accounts:login'
    ), name='logout'),

    # Optional: Custom profile view
    path('profile/', views.profile_view, name='profile'),
]