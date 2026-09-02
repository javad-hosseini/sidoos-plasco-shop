from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.products.models import ProductLike, ProductSave


@login_required
def profile_view(request):
    """Profile page with user's saved and liked products."""
    saved_entries = (
        ProductSave.objects.filter(user=request.user, product__published=True)
        .select_related('product', 'product__category')
        .order_by('-created_at')
    )
    liked_entries = (
        ProductLike.objects.filter(user=request.user, product__published=True)
        .select_related('product', 'product__category')
        .order_by('-created_at')
    )

    return render(request, 'accounts/profile.html', {
        'saved_entries': saved_entries,
        'liked_entries': liked_entries,
    })