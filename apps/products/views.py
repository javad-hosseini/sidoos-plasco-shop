from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import Product, ProductImage, ProductSave, ProductLike


def product_list(request):
    """Display all published products with pagination."""
    products = Product.objects.filter(published=True).prefetch_related('images', 'tags')
    
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'products': page_obj.object_list,
    }
    return render(request, 'products/product_list.html', context)


def product_detail(request, slug):
    """Display detailed product information."""
    product = get_object_or_404(Product, slug=slug, published=True)
    images = product.images.all()
    tags = product.tags.all()
    
    # Check if user has saved/liked this product
    is_saved = False
    is_liked = False
    if request.user.is_authenticated:
        is_saved = ProductSave.objects.filter(user=request.user, product=product).exists()
        is_liked = ProductLike.objects.filter(user=request.user, product=product).exists()
    
    context = {
        'product': product,
        'images': images,
        'tags': tags,
        'is_saved': is_saved,
        'is_liked': is_liked,
        'discount': product.get_discount_percentage(),
    }
    return render(request, 'products/product_detail.html', context)


def special_sales(request):
    """Display products featured in special sales."""
    products = Product.objects.filter(published=True, featured_in_special_sales=True).prefetch_related('images', 'tags')
    
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'title': 'Special Sales',
    }
    return render(request, 'products/special_sales.html', context)
