import ipaddress
import logging
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import IntegrityError
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.blogs.models import Article
from apps.products.models import Product
from .forms import ContactForm, NewsletterSubscriptionForm
from .models import (
    BestSeller,
    FeaturedCategory,
    HeroSlide,
    NewsletterSubscriber,
    PriceList,
    SpecialSaleFeature,
)

logger = logging.getLogger(__name__)

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

    best_sellers = (
        BestSeller.objects.filter(
            is_active=True,
            product__published=True,
        ).select_related("product", "product__category")[:BEST_SELLERS_LIMIT]
    )

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
        "# LLM / Agent Documentation (llmstxt.org specification)",
        "User-agent: GPTBot",
        "Allow: /llms.txt",
        "User-agent: ClaudeBot",
        "Allow: /llms.txt",
        "User-agent: PerplexityBot",
        "Allow: /llms.txt",
        "User-agent: Google-Extended",
        "Allow: /llms.txt",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def llms_txt(request):
    """
    Serve structured Markdown site documentation for AI search crawlers (llmstxt.org).
    Provides company context, product categories, wholesale purchasing guidelines, and site links.
    """
    base_url = request.build_absolute_uri("/").rstrip("/")
    content = f"""# سیدوس | Sidoos

> کارخانه و مرکز تولید و پخش عمده گلدان‌های پلاستیکی، ظروف خانه و ملزومات دکوراتیو با کیفیت صادراتی در مشهد و سراسر ایران.

## درباره شرکت
سیدوس تولیدکننده پیشرو در صنایع پلاستیک و دکوراتیو خانگی است که محصولات خود را به صورت مستقیم و بدون واسطه به مغازه‌داران، فروشگاه‌ها، عمده‌فروشان و صادرکنندگان سراسر کشور عرضه می‌کند.

- وب‌سایت: {base_url}
- دفتر مرکزی: مشهد، بلوار وکیل‌آباد
- تلفن همراه و واتساپ: 09308743868
- تلفن‌های ثابت: 05138944687 و 05138944715
- ساعت پاسخگویی: شنبه تا چهارشنبه ۸:۰۰ الی ۱۸:۰۰

## بخش‌های اصلی سایت
- [صفحه اصلی]({base_url}/): معرفی محصولات منتخب، جدیدترین اقلام و پرفروش‌ها
- [کاتالوگ فروشگاه]({base_url}/products/): کاتالوگ جامع محصولات همراه با مشخصات فنی و گالری تصاویر
- [فروش ویژه و تخفیف‌ها]({base_url}/products/special-sales/): محصولات دارای تخفیف دوره‌ای و پیشنهادهای همکاری
- [مجله و مقالات سیدوس]({base_url}/blogs/): راهنمای نگهداری گیاهان، انتخاب گلدان مناسب، و نکات دکوراسیون داخلی
- [تماس با ما]({base_url}/contact/): شماره‌های تماس، موقعیت مکانی و فرم ارتباط مستقیم
- [سوالات متداول]({base_url}/faq/): پرسش‌های پرتکرار درباره حداقل تیراژ سفارش، نحوه پرداخت و باربری
- [شرایط و روش‌های ارسال]({base_url}/shipping/): اطلاعات ارسال سریع با باربری و بیمه مرسولات
- [راهنمای خرید]({base_url}/guide/): مراحل سفارش عمده و استعلام قیمت

## دسته‌بندی‌های محصولات
- گلدان‌های پلاستیکی و آپارتمانی
- آبپاش‌ها و ابزار باغبانی
- ظروف دکوراتیو و مدرن
- ملزومات آشپزخانه و پلاسکو
- اتصالات و قطعات بهداشتی ساختمانی

## شرایط خرید عمده و استعلام قیمت
تمامی محصولات در کارتن‌های مادر استاندارد بسته‌بندی شده‌اند. استعلام قیمت همکاری از طریق ثبت‌نام در سایت یا تماس مستقیم با کارشناسان فروش امکان‌پذیر است.
"""
    return HttpResponse(content.strip() + "\n", content_type="text/plain; charset=utf-8")


@login_required
def price_list_download(request, pk):
    """
    Secure download view for authenticated users to access administrative price-list files.

    Security guarantees:
    - Requires active user authentication (@login_required).
    - Fetches only existing, active PriceList objects by database ID (pk) — never user-supplied file paths.
    - Checks whether the physical file exists in storage before attempting retrieval.
    - Serves through Django FileResponse as an attachment to avoid inline script execution.
    - Raises Http404 on missing or non-existent files.
    """
    price_list = get_object_or_404(PriceList, pk=pk, is_active=True)

    if not price_list.file:
        raise Http404("فایل مورد نظر یافت نشد.")

    try:
        if not price_list.file.storage.exists(price_list.file.name):
            raise Http404("فایل مورد نظر در سرور یافت نشد.")
        file_obj = price_list.file.open("rb")
    except (OSError, ValueError):
        raise Http404("خطا در باز کردن فایل مورد نظر.")

    filename = os.path.basename(price_list.file.name)
    response = FileResponse(file_obj, as_attachment=True, filename=filename)
    return response


@login_required
def price_list_api(request):
    """Return JSON list of available price lists for authenticated users."""
    items = PriceList.objects.filter(is_active=True).order_by("order", "-created_at")
    data = [
        {
            "id": item.pk,
            "title": item.title,
            "description": item.description,
            "file_type": item.get_file_extension(),
            "file_size": item.get_file_size_formatted(),
            "download_url": item.get_download_url(),
        }
        for item in items
    ]
    return JsonResponse({"success": True, "price_lists": data})


def contact_us(request):
    """Contact page with contact details, social media, working hours, and inquiry form."""
    sent = False
    error_message = None

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            try:
                contact_msg = form.save(commit=False)
                if request.user.is_authenticated:
                    contact_msg.user = request.user

                # Capture and sanitize client IP
                raw_ip = None
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    raw_ip = x_forwarded_for.split(',')[0].strip()
                elif request.META.get('REMOTE_ADDR'):
                    raw_ip = request.META.get('REMOTE_ADDR').strip()

                valid_ip = None
                if raw_ip:
                    try:
                        ipaddress.ip_address(raw_ip)
                        valid_ip = raw_ip
                    except ValueError:
                        valid_ip = None
                contact_msg.ip_address = valid_ip
                contact_msg.save()
                sent = True

                # Send email notification to support@sidoos.ir
                try:
                    subject_display = contact_msg.get_subject_display()
                    clean_name = " ".join(contact_msg.name.split())
                    email_subject = f"[فرم تماس] پیام جدید از {clean_name} - {subject_display}"
                    email_body = f"""یک پیام جدید از طریق فرم تماس با ما سایت سیدوس دریافت شد:

• نام و نام خانوادگی: {contact_msg.name}
• شماره تماس: {contact_msg.phone}
• موضوع: {subject_display}
• تاریخ ارسال: {timezone.now().strftime('%Y-%m-%d %H:%M')}

متن پیام:
----------------------------------------
{contact_msg.message}
----------------------------------------

⚠️ هشدار مهم به اپراتور / همکار گرامی:
لطفاً به این ایمیل پاسخ (Reply) ندهید. این پیام از طریق فرم تماس وب‌سایت ارسال شده است و پاسخ ایمیلی به دست مشتری نمی‌رسد. برای پاسخ‌گویی، حتماً از طریق تماس تلفنی با شماره فوق ({contact_msg.phone}) ارتباط بگیرید یا در صورت نیاز وضعیت پیام را در پنل مدیریت به‌روزرسانی نمایید.
"""
                    send_mail(
                        subject=email_subject,
                        message=email_body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=["support@sidoos.ir"],
                        fail_silently=True,
                    )
                except Exception as mail_err:
                    logger.warning("Failed to send contact notification email: %s", mail_err)

                # Reset form with initial user data if authenticated
                initial_data = {}
                if request.user.is_authenticated:
                    initial_data["name"] = request.user.get_full_name() or request.user.username
                    if hasattr(request.user, "phone_number") and request.user.phone_number:
                        initial_data["phone"] = request.user.phone_number
                form = ContactForm(initial=initial_data)

            except Exception as e:
                logger.exception("Error saving contact message: %s", e)
                error_message = "متأسفانه در ثبت پیام خطایی رخ داد. لطفاً مجدداً تلاش فرمایید یا با شماره‌های شرکت تماس بگیرید."
    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data["name"] = request.user.get_full_name() or request.user.username
            if hasattr(request.user, "phone_number") and request.user.phone_number:
                initial_data["phone"] = request.user.phone_number
        form = ContactForm(initial=initial_data)

    return render(request, 'home/contact.html', {'sent': sent, 'form': form, 'error_message': error_message})


def purchase_guide(request):
    """Customer purchase guide page."""
    return render(request, 'home/purchase_guide.html')


def shipping_terms(request):
    """Shipping methods and delivery terms page."""
    return render(request, 'home/shipping_terms.html')


def return_policy(request):
    """Return and replacement policy page."""
    return render(request, 'home/return_policy.html')


def faq(request):
    """Frequently asked questions page."""
    return render(request, 'home/faq.html')