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


class FeaturedCategory(models.Model):
    """
    A category selected by the admin to appear in the "Featured Categories"
    section of the homepage, paired with a homepage-only cover image.

    Category itself carries no image field (it's a pure taxonomy), so the
    homepage cover image lives here instead of being bolted onto Category.
    """

    category = models.OneToOneField(
        "products.Category",
        on_delete=models.CASCADE,
        related_name="home_featured",
        verbose_name="دسته‌بندی",
        help_text="دسته‌بندی‌ای که در بخش «دسته‌بندی‌های منتخب» صفحه اصلی نمایش داده می‌شود.",
    )

    image = models.ImageField(
        upload_to="home/featured_categories/",
        verbose_name="تصویر",
        help_text="تصویری که مخصوص نمایش این دسته‌بندی در صفحه اصلی است (مستقل از خود دسته‌بندی).",
    )

    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش",
        help_text="عدد کوچک‌تر = نمایش جلوتر در بخش دسته‌بندی‌های منتخب.",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال",
        help_text="اگر غیرفعال باشد، این دسته‌بندی در صفحه اصلی نمایش داده نمی‌شود.",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")

    class Meta:
        verbose_name = "دسته‌بندی منتخب"
        verbose_name_plural = "دسته‌بندی‌های منتخب"
        ordering = ["display_order", "-created_at"]
        indexes = [
            models.Index(fields=["is_active", "display_order"]),
        ]

    def __str__(self):
        status = "فعال" if self.is_active else "غیرفعال"
        return f"{self.category.name} ({status})"


class SpecialSaleFeature(models.Model):
    """
    A product selected by the admin to appear in the "Special Sale" section
    of the homepage.

    Only products with Product.featured_in_special_sales enabled may be
    selected. This is enforced at the field level via limit_choices_to
    (which Django's admin honors both for the autocomplete search results
    and for form validation), and again in clean() so the rule also holds
    for saves that don't go through a ModelForm.
    """

    product = models.OneToOneField(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="home_special_sale",
        limit_choices_to={"featured_in_special_sales": True},
        verbose_name="محصول",
        help_text="فقط محصولاتی که «فروش ویژه» آن‌ها فعال است قابل انتخاب هستند.",
    )

    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش",
        help_text="عدد کوچک‌تر = نمایش جلوتر در بخش فروش ویژه.",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال",
        help_text="اگر غیرفعال باشد، محصول در بخش فروش ویژه نمایش داده نمی‌شود.",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")

    class Meta:
        verbose_name = "محصول فروش ویژه"
        verbose_name_plural = "محصولات فروش ویژه"
        ordering = ["display_order", "-created_at"]
        indexes = [
            models.Index(fields=["is_active", "display_order"]),
        ]

    def __str__(self):
        status = "فعال" if self.is_active else "غیرفعال"
        return f"{self.product.name} ({status})"

    def clean(self):
        """Validate that the selected product actually has the special-sale flag on."""
        super().clean()
        if self.product_id and not self.product.featured_in_special_sales:
            raise ValidationError({
                "product": _(
                    "فقط محصولاتی که «فروش ویژه» برای آن‌ها فعال است قابل انتخاب هستند."
                ),
            })

    def save(self, *args, **kwargs):
        # Enforce the special-sale restriction even for saves that bypass a
        # ModelForm (shell, scripts, etc.), not just admin-form validation.
        self.full_clean()
        super().save(*args, **kwargs)


class NewsletterSubscriber(models.Model):
    """
    An email address collected from the homepage newsletter signup form.

    Public-facing: only ever created through the newsletter subscribe
    endpoint, never read back out through any public view or API - the
    admin list is the only place these are visible.
    """

    email = models.EmailField(
        unique=True,
        verbose_name="ایمیل",
        help_text="آدرسی که کاربر برای عضویت در خبرنامه سیدوس وارد کرده است. هر ایمیل فقط یک‌بار می‌تواند ثبت شود.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ثبت‌نام",
        help_text="تاریخ و زمان عضویت در خبرنامه (به‌صورت خودکار ثبت می‌شود).",
    )

    class Meta:
        verbose_name = "مشترک خبرنامه"
        verbose_name_plural = "مشترکین خبرنامه"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
