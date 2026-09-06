from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.blogs.models import Article
from apps.products.models import Product
from .forms import NewsletterSubscriptionForm
from .models import BestSeller, FeaturedCategory, HeroSlide, NewsletterSubscriber, SpecialSaleFeature

# How many items each homepage section shows at most.
FEATURED_LIMIT = 12
BEST_SELLERS_LIMIT = 8
FEATURED_CATEGORIES_LIMIT = 8
SPECIAL_OFFERS_LIMIT = 12
LATEST_ARTICLES_LIMIT = 6


def home(request):
    """Public landing page, assembled from admin-managed content."""
    hero_slides = HeroSlide.objects.filter(is_active=True)

    featured_products = (
        Product.objects.filter(published=True, is_featured=True)
        .order_by("featured_order", "-created_at")[:FEATURED_LIMIT]
    )

    best_sellers = [
        entry.product
        for entry in BestSeller.objects.filter(
            is_active=True,
            product__published=True,
        ).select_related("product", "product__category")[:BEST_SELLERS_LIMIT]
    ]

    featured_categories = (
        FeaturedCategory.objects.filter(is_active=True)
        .select_related("category")[:FEATURED_CATEGORIES_LIMIT]
    )

    special_offers = [
        entry.product
        for entry in SpecialSaleFeature.objects.filter(
            is_active=True,
            product__published=True,
            product__featured_in_special_sales=True,
        ).select_related("product", "product__category")
        .prefetch_related("product__images")[:SPECIAL_OFFERS_LIMIT]
    ]

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
        "best_sellers": best_sellers,
        "featured_categories": featured_categories,
        "special_offers": special_offers,
        "latest_articles": latest_articles,
        "can_view_price": can_view_price,
    }
    return render(request, "home/index.html", context)


@require_POST
def newsletter_subscribe(request):
    """
    Handle the homepage newsletter signup form (AJAX POST, same convention
    as apps.products.views.toggle_save/toggle_like: CSRF-protected JSON
    endpoint, always 200 unless the submitted data itself is invalid).
    """
    form = NewsletterSubscriptionForm(request.POST)

    if not form.is_valid():
        message = form.errors["email"][0] if "email" in form.errors else "لطفاً یک ایمیل معتبر وارد کنید."
        return JsonResponse({"success": False, "message": message}, status=400)

    email = form.cleaned_data["email"].lower()

    if NewsletterSubscriber.objects.filter(email=email).exists():
        return JsonResponse({
            "success": False,
            "already_subscribed": True,
            "message": "این ایمیل قبلاً در خبرنامه سیدوس ثبت شده است.",
        })

    try:
        NewsletterSubscriber.objects.create(email=email)
    except IntegrityError:
        # Two simultaneous submissions of the same address raced past the
        # .exists() check above; the unique constraint caught it instead.
        return JsonResponse({
            "success": False,
            "already_subscribed": True,
            "message": "این ایمیل قبلاً در خبرنامه سیدوس ثبت شده است.",
        })

    return JsonResponse({
        "success": True,
        "message": "با موفقیت در خبرنامه سیدوس عضو شدید.",
    })


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
        "Disallow: /newsletter/",
        "Sitemap: " + request.build_absolute_uri("/sitemap.xml"),
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")