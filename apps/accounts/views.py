from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.home.models import PriceList
from apps.products.models import ProductLike, ProductSave


@login_required
def profile_view(request):
    """Profile page with user's saved and liked products and downloadable price lists."""
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
    price_lists = PriceList.objects.filter(is_active=True).order_by('order', '-created_at')

    return render(request, 'accounts/profile.html', {
        'saved_entries': saved_entries,
        'liked_entries': liked_entries,
        'price_lists': price_lists,
    })