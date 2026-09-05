from django.contrib import admin
from django.utils.html import format_html

from .models import BestSeller, FeaturedCategory, HeroSlide, NewsletterSubscriber, SpecialSaleFeature


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = (
        "preview",
        "eyebrow",
        "cta_label",
        "cta_url_name",
        "is_active",
        "order",
    )
    list_editable = ("is_active", "order")
    list_filter = ("is_active",)
    search_fields = ("title", "eyebrow", "subtitle")
    readonly_fields = ("created_at", "updated_at", "image_tag")

    fieldsets = (
        ("متن اسلاید", {
            "fields": ("eyebrow", "title", "subtitle"),
        }),
        ("تصویر", {
            "fields": ("background_image", "image_tag"),
        }),
        ("دکمه فراخوان (CTA)", {
            "fields": ("cta_label", "cta_url_name"),
            "description": "اگر متن دکمه خالی باشد، دکمه‌ای نمایش داده نمی‌شود.",
        }),
        ("نمایش", {
            "fields": ("is_active", "order"),
        }),
        ("زمان‌بندی", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="عنوان")
    def preview(self, obj):
        first_line = obj.title.splitlines()[0] if obj.title else ""
        return first_line or f"اسلاید {obj.pk}"

    @admin.display(description="پیش‌نمایش تصویر")
    def image_tag(self, obj):
        if obj.background_image:
            return format_html(
                '<img src="{}" style="max-height:160px;border-radius:8px;" />',
                obj.background_image.url,
            )
        return "-"


@admin.register(BestSeller)
class BestSellerAdmin(admin.ModelAdmin):
    """
    Django admin configuration for the BestSeller model.

    Provides an inline-style preview, filtering, search, and editable
    ordering/activation controls from the admin list view.
    """

    list_display = (
        "product_preview",
        "product_name",
        "subtitle",
        "is_active",
        "display_order",
    )
    list_editable = ("is_active", "display_order")
    list_filter = ("is_active", "product__category")
    search_fields = ("product__name", "subtitle")
    readonly_fields = ("created_at", "updated_at", "product_image_tag")
    autocomplete_fields = ("product",)

    fieldsets = (
        ("محصول", {
            "fields": ("product", "product_image_tag"),
            "description": "محصولی که می‌خواهید در بخش پرفروش‌های صفحه اصلی نمایش داده شود.",
        }),
        ("متن نمایشی", {
            "fields": ("subtitle",),
            "description": "زیرعنوان اختیاری که زیر نام محصول نمایش داده می‌شود.",
        }),
        ("نمایش و ترتیب", {
            "fields": ("is_active", "display_order"),
            "description": "برای نمایش در صفحه اصلی، «فعال» را روشن کنید و ترتیب را تعیین کنید.",
        }),
        ("زمان‌بندی", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="نام محصول")
    def product_name(self, obj):
        """Return the product's name for the admin list display."""
        return obj.product.name

    @admin.display(description="دسته‌بندی")
    def product_category(self, obj):
        """Return the product's category name if it exists."""
        return obj.product.category.name if obj.product.category else "-"

    @admin.display(description="پیش‌نمایش")
    def product_preview(self, obj):
        """Return a short preview combining product name and status."""
        status = "✅" if obj.is_active else "⛔"
        return f"{status} {obj.product.name[:40]}"

    @admin.display(description="تصویر محصول")
    def product_image_tag(self, obj):
        """Render a thumbnail of the product's cover image."""
        if obj.product.cover_image:
            return format_html(
                '<img src="{}" style="max-height:120px;border-radius:8px;" />',
                obj.product.cover_image.url,
            )
        return "-"


@admin.register(FeaturedCategory)
class FeaturedCategoryAdmin(admin.ModelAdmin):
    """
    Django admin configuration for the FeaturedCategory model.

    Lets admins search existing categories, assign a homepage-only cover
    image to each, and control ordering/visibility from the list view.
    """

    list_display = (
        "category_preview",
        "category_name",
        "is_active",
        "display_order",
    )
    list_editable = ("is_active", "display_order")
    list_filter = ("is_active",)
    search_fields = ("category__name",)
    readonly_fields = ("created_at", "updated_at", "category_image_tag")
    autocomplete_fields = ("category",)

    fieldsets = (
        ("دسته‌بندی", {
            "fields": ("category",),
            "description": "دسته‌بندی‌ای که می‌خواهید در بخش دسته‌بندی‌های منتخب صفحه اصلی نمایش داده شود.",
        }),
        ("تصویر", {
            "fields": ("image", "category_image_tag"),
            "description": "تصویری مخصوص نمایش این دسته‌بندی در صفحه اصلی (خود دسته‌بندی تصویری ندارد).",
        }),
        ("نمایش و ترتیب", {
            "fields": ("is_active", "display_order"),
            "description": "برای نمایش در صفحه اصلی، «فعال» را روشن کنید و ترتیب را تعیین کنید.",
        }),
        ("زمان‌بندی", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="نام دسته‌بندی")
    def category_name(self, obj):
        """Return the category's name for the admin list display."""
        return obj.category.name

    @admin.display(description="پیش‌نمایش")
    def category_preview(self, obj):
        """Return a short preview combining category name and status."""
        status = "✅" if obj.is_active else "⛔"
        return f"{status} {obj.category.name[:40]}"

    @admin.display(description="تصویر")
    def category_image_tag(self, obj):
        """Render a thumbnail of the homepage cover image."""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:120px;border-radius:8px;" />',
                obj.image.url,
            )
        return "-"


@admin.register(SpecialSaleFeature)
class SpecialSaleFeatureAdmin(admin.ModelAdmin):
    """
    Django admin configuration for the SpecialSaleFeature model.

    The `product` field only accepts/shows products with
    Product.featured_in_special_sales enabled - enforced by the field's
    limit_choices_to, which the autocomplete widget and form validation
    both honor.
    """

    list_display = (
        "product_preview",
        "product_name",
        "is_active",
        "display_order",
    )
    list_editable = ("is_active", "display_order")
    list_filter = ("is_active", "product__category")
    search_fields = ("product__name",)
    readonly_fields = ("created_at", "updated_at", "product_image_tag")
    autocomplete_fields = ("product",)

    fieldsets = (
        ("محصول", {
            "fields": ("product", "product_image_tag"),
            "description": (
                "محصولی که می‌خواهید در بخش فروش ویژه صفحه اصلی نمایش داده شود. "
                "فقط محصولاتی که «فروش ویژه» آن‌ها فعال است قابل انتخاب‌اند."
            ),
        }),
        ("نمایش و ترتیب", {
            "fields": ("is_active", "display_order"),
            "description": "برای نمایش در صفحه اصلی، «فعال» را روشن کنید و ترتیب را تعیین کنید.",
        }),
        ("زمان‌بندی", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="نام محصول")
    def product_name(self, obj):
        """Return the product's name for the admin list display."""
        return obj.product.name

    @admin.display(description="پیش‌نمایش")
    def product_preview(self, obj):
        """Return a short preview combining product name and status."""
        status = "✅" if obj.is_active else "⛔"
        return f"{status} {obj.product.name[:40]}"

    @admin.display(description="تصویر محصول")
    def product_image_tag(self, obj):
        """Render a thumbnail of the product's cover image."""
        if obj.product.cover_image:
            return format_html(
                '<img src="{}" style="max-height:120px;border-radius:8px;" />',
                obj.product.cover_image.url,
            )
        return "-"


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    """
    Read-mostly admin for newsletter signups collected from the homepage.

    Subscribers are only ever created through the public signup form, so
    adding one manually is disabled here - same convention as
    apps.products.admin.ProductSave/ProductLike.
    """

    list_display = ("email", "created_at")
    search_fields = ("email",)
    ordering = ("-created_at",)
    readonly_fields = ("email", "created_at")

    def has_add_permission(self, request):
        # مشترکین فقط از طریق فرم خبرنامه در صفحه اصلی سایت ثبت می‌شوند.
        return False
