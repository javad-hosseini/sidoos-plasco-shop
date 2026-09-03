from django.shortcuts import render
from django.http import HttpResponse

from apps.blogs.models import Article
from apps.products.models import Product
from .models import HeroSlide

# How many items each homepage section shows at most.
FEATURED_LIMIT = 12
SPECIAL_OFFERS_LIMIT = 12
LATEST_ARTICLES_LIMIT = 6


def home(request):
    """Public landing page, assembled from admin-managed content."""
    hero_slides = HeroSlide.objects.filter(is_active=True)

    featured_products = (
        Product.objects.filter(published=True, is_featured=True)
        .order_by("featured_order", "-created_at")[:FEATURED_LIMIT]
    )

    special_offers = (
        Product.objects.filter(published=True, featured_in_special_sales=True)
        .select_related("category")
        .prefetch_related("images")
        .order_by("-created_at")[:SPECIAL_OFFERS_LIMIT]
    )

    latest_articles = (
        Article.objects.filter(is_published=True)
        .order_by("-published_at", "-created_at")
        .prefetch_related("tags")[:LATEST_ARTICLES_LIMIT]
    )

    can_view_price = (
        request.user.is_authenticated
        and getattr(request.user, "has_price_access", False)
    )

    context = {
        "hero_slides": hero_slides,
        "featured_products": featured_products,
        "special_offers": special_offers,
        "latest_articles": latest_articles,
        "can_view_price": can_view_price,
    }
    return render(request, "home/index.html", context)


def robots_txt(request):
    """Serve crawler policy without exposing private application routes."""
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /accounts/",
        "Disallow: /support/",
        "Disallow: /sidoos-administration/",
        "Disallow: /ckeditor5/",
        "Disallow: /products/api/",
        "Sitemap: " + request.build_absolute_uri("/sitemap.xml"),
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")
