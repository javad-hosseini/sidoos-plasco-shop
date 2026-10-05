from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.blogs.models import Article
from apps.products.models import Category, Product


@staff_member_required
@require_GET
def admin_internal_link_search(request):
    """
    Search products, articles, and categories for the CKEditor 5 internal link helper.
    Only accessible by staff users in the admin panel.

    Query parameters:
        q: Search query string (name/title or slug). If empty, returns recent items.
        type: Filter items ('all', 'product', 'article', 'category'). Default: 'all'.
        limit: Maximum results per category (default: 10, max: 30).
    """
    query = request.GET.get('q', '').strip()
    item_type = request.GET.get('type', 'all').lower()

    try:
        limit = min(max(int(request.GET.get('limit', 10)), 1), 30)
    except (ValueError, TypeError):
        limit = 10

    results = []

    # 1. Products
    if item_type in ('all', 'product'):
        prod_qs = Product.objects.select_related('category')
        if query:
            prod_qs = prod_qs.filter(
                Q(name__icontains=query) | Q(slug__icontains=query)
            )
        else:
            prod_qs = prod_qs.order_by('-created_at')

        products = prod_qs[:limit]
        for prod in products:
            meta_parts = []
            if prod.category:
                meta_parts.append(f"دسته‌بندی: {prod.category.name}")
            if prod.call_for_price:
                meta_parts.append("تماس بگیرید")
            elif prod.price:
                meta_parts.append(f"{prod.price:,} تومان")
            if not prod.published:
                meta_parts.append("پیش‌نویس")

            thumbnail_url = prod.cover_image.url if prod.cover_image else None

            results.append({
                'id': prod.pk,
                'type': 'product',
                'type_label': 'محصول',
                'title': prod.name,
                'url': f"/products/{prod.slug}/",
                'meta': ' • '.join(meta_parts),
                'thumbnail': thumbnail_url,
                'published': prod.published,
            })

    # 2. Articles
    if item_type in ('all', 'article'):
        art_qs = Article.objects.all()
        if query:
            art_qs = art_qs.filter(
                Q(title__icontains=query) | Q(slug__icontains=query)
            )
        else:
            art_qs = art_qs.order_by('-created_at')

        articles = art_qs[:limit]
        for art in articles:
            meta_parts = []
            if art.reading_time:
                meta_parts.append(f"زمان مطالعه: {art.reading_time} دقیقه")
            if not art.is_published:
                meta_parts.append("پیش‌نویس")

            thumbnail_url = art.featured_image.url if art.featured_image else None

            results.append({
                'id': art.pk,
                'type': 'article',
                'type_label': 'مقاله',
                'title': art.title,
                'url': f"/blogs/{art.slug}/",
                'meta': ' • '.join(meta_parts),
                'thumbnail': thumbnail_url,
                'published': art.is_published,
            })

    # 3. Categories
    if item_type in ('all', 'category'):
        cat_qs = Category.objects.select_related('parent')
        if query:
            cat_qs = cat_qs.filter(
                Q(name__icontains=query) | Q(slug__icontains=query)
            )
        else:
            cat_qs = cat_qs.order_by('-created_at')

        categories = cat_qs[:limit]
        for cat in categories:
            parent_name = cat.parent.name if cat.parent else "شاخه اصلی"
            results.append({
                'id': cat.pk,
                'type': 'category',
                'type_label': 'دسته‌بندی',
                'title': cat.name,
                'url': f"/products/categories/{cat.slug}/",
                'meta': f"والد: {parent_name}",
                'thumbnail': None,
                'published': True,
            })

    # If 'all' is chosen and user searched with a keyword, rank results by title match
    if query and item_type == 'all':
        def _relevance_sort(item):
            # Prioritize exact start match on title
            lower_title = item['title'].lower()
            lower_q = query.lower()
            if lower_title == lower_q:
                return 0
            if lower_title.startswith(lower_q):
                return 1
            return 2

        results.sort(key=_relevance_sort)

    return JsonResponse({'results': results})
