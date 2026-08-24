# apps/accounts/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

def profile_view(request):
    """Simple profile view to show user info after login"""
    return render(request, 'accounts/profile.html', {
        'user': request.user,
    })