from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_POST

from .forms import CategoryForm
from .models import Category, Product, ProductImage, ProductSave, ProductLike


def _can_view_price(user):
    return user.is_authenticated and user.has_price_access


def product_list(request):
    """Display all published products with pagination."""
    can_view_price = _can_view_price(request.user)
    products = (
        Product.objects.filter(published=True)
        .select_related('category')
        .prefetch_related('images', 'tags')
    )
    
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'selected_category': None,
        'can_view_price': can_view_price,
    }
    return render(request, 'products/product_list.html', context)


def product_detail(request, slug):
    """Display detailed product information."""
    can_view_price = _can_view_price(request.user)
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
        'discount': product.get_discount_percentage() if can_view_price else None,
        'can_view_price': can_view_price,
    }
    return render(request, 'products/product_detail.html', context)


def special_sales(request):
    """Display products featured in special sales."""
    can_view_price = _can_view_price(request.user)
    products = (
        Product.objects.filter(published=True, featured_in_special_sales=True)
        .select_related('category')
        .prefetch_related('images', 'tags')
    )
    
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'title': 'Special Sales',
        'selected_category': None,
        'can_view_price': can_view_price,
    }
    return render(request, 'products/special_sales.html', context)


def category_products(request, slug):
    """Display published products under a category and all nested subcategories."""
    can_view_price = _can_view_price(request.user)
    selected_category = get_object_or_404(Category, slug=slug)
    category_ids = selected_category.get_descendant_ids()
    products = (
        Product.objects.filter(published=True, category_id__in=category_ids)
        .select_related('category')
        .prefetch_related('images', 'tags')
    )

    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'selected_category': selected_category,
        'can_view_price': can_view_price,
    }
    return render(request, 'products/product_list.html', context)


def category_list(request):
    """Display all categories and their direct subcategories."""
    categories = (
        Category.objects.filter(parent__isnull=True)
        .prefetch_related('children')
        .annotate(product_count=Count('products'))
        .order_by('name')
    )
    return render(request, 'products/category_list.html', {'categories': categories})


@login_required
def category_create(request):
    """Create a new category or subcategory."""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.creator = request.user
            try:
                category.full_clean()
            except ValidationError as exc:
                for errors in exc.message_dict.values():
                    for error in errors:
                        form.add_error(None, error)
            else:
                category.save()
                messages.success(request, 'Category created successfully.')
                return redirect('products:category_list')
    else:
        form = CategoryForm()

    return render(request, 'products/category_create.html', {'form': form})


@login_required
@require_POST
def toggle_save(request, product_id):
    product = get_object_or_404(Product, id=product_id, published=True)
    save, created = ProductSave.objects.get_or_create(user=request.user, product=product)
    if not created:
        save.delete()
    return JsonResponse({'saved': created})


@login_required
@require_POST
def toggle_like(request, product_id):
    product = get_object_or_404(Product, id=product_id, published=True)
    like, created = ProductLike.objects.get_or_create(user=request.user, product=product)
    if not created:
        like.delete()
    return JsonResponse({'liked': created})
