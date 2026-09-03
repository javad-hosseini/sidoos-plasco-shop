"""
Home application models.

Contains content models that power the public landing page and are
managed entirely from the Django admin:

- HeroSlide: one slide of the homepage hero slider.
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import NoReverseMatch, reverse
from django.utils.translation import gettext_lazy as _


class HeroSlide(models.Model):
    """
    A single slide in the homepage hero slider.

    Every visible text fragment of the slide is a separate field so the
    marketing team can edit them independently from the admin. The CTA
    destination is chosen from a fixed list of parameterless named URLs.
    """

    # Named URLs that can be safely reversed without extra arguments.
    # Routes that require a slug / id / tracking code are intentionally
    # excluded — the hero CTA always points at a top-level page.
    CTA_URL_CHOICES = [
        ("home:home", "خانه"),
        ("products:product_list", "فروشگاه (همه محصولات)"),
        ("products:special_sales", "فروش ویژه"),
        ("products:category_list", "دسته‌بندی‌ها"),
        ("blogs:article_list", "مجله سیدوس"),
        ("support:ticket_list", "پشتیبانی (لیست تیکت‌ها)"),
        ("support:ticket_create", "ثبت تیکت جدید"),
        ("accounts:login", "ورود"),
        ("accounts:logout", "خروج"),
        ("accounts:profile", "پروفایل کاربر"),
    ]

    background_image = models.ImageField(
        upload_to="home/hero/",
        verbose_name="تصویر پس‌زمینه",
        help_text="تصویر تمام‌صفحه پشت متن اسلاید. بهتر است افقی و با کیفیت باشد.",
    )
    eyebrow = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="پیش‌عنوان",
        help_text="متن کوچک بالای عنوان (مثلاً «مجموعه‌ی پاییز ۱۴۰۳»).",
    )
    title = models.TextField(
        verbose_name="عنوان اصلی",
        help_text="عنوان بزرگ اسلاید. برای شکستن خط، Enter بزنید.",
    )
    subtitle = models.TextField(
        blank=True,
        verbose_name="توضیح کوتاه",
        help_text="یک یا دو جمله زیر عنوان.",
    )
    cta_label = models.CharField(
        max_length=60,
        blank=True,
        verbose_name="متن دکمه",
        help_text="متن روی دکمه‌ی طلایی. خالی بگذارید تا دکمه نمایش داده نشود.",
    )
    cta_url_name = models.CharField(
        max_length=64,
        blank=True,
        choices=CTA_URL_CHOICES,
        verbose_name="مقصد دکمه",
        help_text="صفحه‌ای که با کلیک روی دکمه باز می‌شود.",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال",
        help_text="غیرفعال کنید تا اسلاید از روی سایت مخفی شود.",
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش",
        help_text="کوچک‌تر = جلوتر.",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "اسلاید هیرو"
        verbose_name_plural = "اسلایدهای هیرو"
        ordering = ["order", "id"]

    def __str__(self):
        first_line = self.title.splitlines()[0] if self.title else ""
        return first_line or f"اسلاید {self.pk}"

    def get_cta_url(self):
        """
        Resolve the CTA destination to a URL path.

        Returns an empty string when no destination is set or the name
        can no longer be reversed, so templates can guard with `if`.
        """
        if not self.cta_url_name:
            return ""
        try:
            return reverse(self.cta_url_name)
        except NoReverseMatch:
            return ""


class BestSeller(models.Model):
    """
    Represents a product selected by the admin to appear in the
    "Best Sellers" section of the homepage.

    A product can only appear once in this section. The ordering is
    controlled by the `display_order` field (smaller values appear first).
    """

    product = models.OneToOneField(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="home_bestseller",
        verbose_name="محصول",
        help_text="محصولی که به‌عنوان پرفروش در صفحه اصلی نمایش داده می‌شود.",
    )

    subtitle = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="زیرعنوان",
        help_text="متن کوتاهی که زیر نام محصول در بخش پرفروش‌ها نمایش داده می‌شود.",
    )

    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش",
        help_text="عدد کوچک‌تر = نمایش جلوتر در بخش پرفروش‌ها.",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال",
        help_text="اگر غیرفعال باشد، محصول در بخش پرفروش‌ها نمایش داده نمی‌شود.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاریخ به‌روزرسانی",
    )

    class Meta:
        verbose_name = "محصول پرفروش"
        verbose_name_plural = "محصولات پرفروش"
        ordering = ["display_order", "-created_at"]
        indexes = [
            models.Index(fields=["is_active", "display_order"]),
        ]

    def __str__(self):
        """Return a human-readable representation of the bestseller entry."""
        status = "فعال" if self.is_active else "غیرفعال"
        return f"{self.product.name} ({status})"

    def clean(self):
        """Validate that the selected product is published."""
        super().clean()
        if self.is_active and self.product and not self.product.published:
            raise ValidationError({
                "product": _(
                    "فقط محصولات منتشرشده می‌توانند به‌عنوان پرفروش فعال نمایش داده شوند."
                ),
            })
