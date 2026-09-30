import urllib.parse
from django.http import HttpResponsePermanentRedirect
from django.utils.encoding import iri_to_uri

from apps.blogs.models import Article
from apps.products.models import Category, Product


class LegacyRedirectMiddleware:
    """
    Middleware to 301-redirect legacy WordPress/WooCommerce URLs
    to new Django endpoints for SEO preservation.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Check if the incoming request matches known legacy prefixes or parameters
        redirect_url = self._check_legacy_request(request)
        if redirect_url:
            return HttpResponsePermanentRedirect(iri_to_uri(redirect_url))

        # 2. Process normal request
        response = self.get_response(request)

        # 3. If response is 404, check fallback matching (e.g. root-level permalinks)
        if response.status_code == 404 and request.method in ('GET', 'HEAD'):
            fallback_url = self._check_404_fallback(request)
            if fallback_url:
                return HttpResponsePermanentRedirect(iri_to_uri(fallback_url))

        return response

    def _check_legacy_request(self, request):
        path = request.path
        decoded_path = urllib.parse.unquote(path).rstrip('/')
        if not decoded_path:
            # Query param redirects on root, e.g. /?p=123 or /?product_cat=slug
            return self._check_query_params(request)

        # Check WordPress query parameters on any path
        qp_redirect = self._check_query_params(request)
        if qp_redirect:
            return qp_redirect

        # Product detail legacy URLs: /product/<slug>/ or /shop/<slug>/
        if decoded_path.startswith('/product/'):
            slug = decoded_path[len('/product/'):].strip('/')
            if slug:
                return f'/products/{slug}/'
            return '/products/'

        if decoded_path == '/product':
            return '/products/'

        if decoded_path == '/shop':
            return '/products/'

        if decoded_path.startswith('/shop/'):
            slug = decoded_path[len('/shop/'):].strip('/')
            if slug:
                return f'/products/{slug}/'
            return '/products/'

        # Product category legacy URLs: /product-category/<path>/ or /product-cat/<path>/
        if decoded_path.startswith('/product-category/'):
            cat_path = decoded_path[len('/product-category/'):].strip('/')
            leaf_slug = cat_path.split('/')[-1] if cat_path else ''
            if leaf_slug:
                return f'/products/categories/{leaf_slug}/'
            return '/products/categories/'

        if decoded_path == '/product-category':
            return '/products/categories/'

        if decoded_path.startswith('/product-cat/'):
            cat_path = decoded_path[len('/product-cat/'):].strip('/')
            leaf_slug = cat_path.split('/')[-1] if cat_path else ''
            if leaf_slug:
                return f'/products/categories/{leaf_slug}/'
            return '/products/categories/'

        # Blog / Mag legacy URLs: /mag/<slug>/ or /blog/<slug>/ or /article/<slug>/
        for blog_prefix in ('/mag/', '/blog/', '/articles/', '/article/'):
            if decoded_path.startswith(blog_prefix):
                slug = decoded_path[len(blog_prefix):].strip('/')
                if slug:
                    return f'/blogs/{slug}/'
                return '/blogs/'

        if decoded_path in ('/mag', '/blog', '/articles', '/article'):
            return '/blogs/'

        # Common WooCommerce / WordPress utility routes
        if decoded_path in ('/cart', '/checkout', '/basket', '/compare'):
            return '/products/'

        if decoded_path in ('/my-account', '/myaccount', '/wishlist'):
            return '/accounts/login/'

        return None

    def _check_query_params(self, request):
        # e.g., ?p=123 or ?page_id=123
        p_id = request.GET.get('p') or request.GET.get('page_id')
        post_type = request.GET.get('post_type')

        if p_id and p_id.isdigit():
            pk = int(p_id)
            if post_type == 'product':
                product = Product.objects.filter(pk=pk).first()
                if product:
                    return f'/products/{product.slug}/'
            else:
                # Check product first, then article
                product = Product.objects.filter(pk=pk).first()
                if product:
                    return f'/products/{product.slug}/'
                article = Article.objects.filter(pk=pk).first()
                if article:
                    return f'/blogs/{article.slug}/'

        # e.g. ?product_cat=slug
        product_cat = request.GET.get('product_cat')
        if product_cat:
            cat_slug = urllib.parse.unquote(product_cat).strip('/')
            return f'/products/categories/{cat_slug}/'

        return None

    def _check_404_fallback(self, request):
        """
        If a URL returned 404, check if it matches a slug in Product, Article, or Category.
        Handles old root permalinks (e.g. domain.com/post-title-or-slug/).
        """
        path = request.path
        decoded_path = urllib.parse.unquote(path).strip('/')

        # Only check single-segment paths to avoid unnecessary DB queries on deep 404 paths
        if not decoded_path or '/' in decoded_path:
            return None

        # Exclude common static/system file patterns
        if '.' in decoded_path:
            return None

        slug = decoded_path
        normalized_slug = slug.replace('_', '-')

        # 1. Product match
        prod = Product.objects.filter(slug=slug).first() or (
            Product.objects.filter(slug=normalized_slug).first() if normalized_slug != slug else None
        )
        if prod:
            return f'/products/{prod.slug}/'

        # 2. Article match
        art = Article.objects.filter(slug=slug).first() or (
            Article.objects.filter(slug=normalized_slug).first() if normalized_slug != slug else None
        )
        if art:
            return f'/blogs/{art.slug}/'

        # 3. Category match
        cat = Category.objects.filter(slug=slug).first() or (
            Category.objects.filter(slug=normalized_slug).first() if normalized_slug != slug else None
        )
        if cat:
            return f'/products/categories/{cat.slug}/'

        return None
