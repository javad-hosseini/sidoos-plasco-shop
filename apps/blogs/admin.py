"""
Django admin configuration for the Sidoos blog application.

This module provides a user-friendly admin interface for managing
articles, optimized for non-technical content managers.
"""

from django import forms
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from taggit.models import Tag

from .models import Article


class PublishedFilter(admin.SimpleListFilter):
    """
    Custom filter for publication status.
    """

    title = _("وضعیت انتشار")
    parameter_name = "publication_status"

    def lookups(self, request, model_admin):
        return [
            ("published", _("منتشر شده")),
            ("draft", _("پیش‌نویس")),
            ("scheduled", _("زمان‌بندی شده")),
        ]

    def queryset(self, request, queryset):
        if self.value() == "published":
            return queryset.filter(
                is_published=True,
                published_at__lte=timezone.now(),
            )
        if self.value() == "draft":
            return queryset.filter(is_published=False)
        if self.value() == "scheduled":
            return queryset.filter(
                is_published=True,
                published_at__gt=timezone.now(),
            )
        return queryset


class HasImageFilter(admin.SimpleListFilter):
    """
    Filter for articles with or without featured images.
    """

    title = _("تصویر شاخص")
    parameter_name = "has_image"

    def lookups(self, request, model_admin):
        return [
            ("yes", _("دارای تصویر")),
            ("no", _("بدون تصویر")),
        ]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.exclude(featured_image="")
        if self.value() == "no":
            return queryset.filter(featured_image="")
        return queryset


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """
    Admin interface for managing articles.
    """

    # List display configuration
    list_display = [
        "title_with_status",
        "featured_image_thumbnail",
        "reading_time_display",
        "publication_status",
        "published_at_display",
        "tags_list",
        "updated_at_display",
    ]

    list_display_links = ["title_with_status"]

    # Filters and search
    list_filter = [
        PublishedFilter,
        HasImageFilter,
        "created_at",
        "updated_at",
    ]

    search_fields = [
        "title",
        "summary",
        "content",
        "slug",
        "meta_title",
        "meta_description",
    ]

    # List pagination
    list_per_page = 20

    # Form layout
    fieldsets = [
        (
            "اطلاعات اصلی",
            {
                "fields": (
                    "title",
                    "slug",
                    "summary",
                    "featured_image",
                    "content",
                ),
                "description": "اطلاعات اصلی مقاله را وارد کنید.",
            },
        ),
        (
            "انتشار و زمان‌بندی",
            {
                "fields": (
                    "is_published",
                    "published_at",
                    "reading_time",
                ),
                "description": "وضعیت انتشار و زمان مطالعه مقاله را مشخص کنید.",
            },
        ),
        (
            "برچسب‌ها",
            {
                "fields": ("tags",),
                "description": "برچسب‌های مرتبط با مقاله را برای نمایش مقالات مرتبط اضافه کنید.",
            },
        ),
        (
            "تنظیمات SEO",
            {
                "fields": (
                    "meta_title",
                    "meta_description",
                    "canonical_url",
                    "robots",
                ),
                "classes": ("collapse",),
                "description": "تنظیمات مربوط به موتورهای جستجو را وارد کنید.",
            },
        ),
        (
            "تنظیمات شبکه‌های اجتماعی",
            {
                "fields": (
                    "og_title",
                    "og_description",
                    "og_image",
                ),
                "classes": ("collapse",),
                "description": "تنظیمات مربوط به اشتراک‌گذاری در شبکه‌های اجتماعی.",
            },
        ),
        (
            "زمان‌بندی خودکار",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
                "description": "این فیلدها به صورت خودکار توسط سیستم ثبت می‌شوند.",
            },
        ),
    ]

    # Read-only fields
    readonly_fields = ["created_at", "updated_at"]

    # Form actions
    actions = [
        "make_published",
        "make_draft",
        "duplicate_articles",
    ]

    # Save behavior
    save_on_top = True
    save_as = True

    def get_queryset(self, request):
        """
        Optimizes the queryset with related fields for better performance.
        """
        return super().get_queryset(request).prefetch_related("tags")

    def get_readonly_fields(self, request, obj=None):
        """
        Returns readonly fields based on the current object state.
        """
        readonly = list(self.readonly_fields)

        if obj and obj.is_published and obj.published_at:
            readonly.append("published_at")

        return readonly

    # ============================================================
    # Custom Display Methods
    # ============================================================

    def title_with_status(self, obj):
        """
        Returns the article title with a status indicator.
        """
        status_color = "green" if obj.is_published else "orange"
        status_text = "منتشر شده" if obj.is_published else "پیش‌نویس"

        return format_html(
            '<span style="font-weight: bold;">{}</span> '
            '<span style="color: {}; font-size: 0.9em;">({})</span>',
            obj.title,
            status_color,
            status_text,
        )

    title_with_status.short_description = "عنوان مقاله"
    title_with_status.admin_order_field = "title"

    def featured_image_thumbnail(self, obj):
        """
        Returns a thumbnail preview of the featured image.
        """
        if obj.featured_image:
            return format_html(
                '<img src="{}" style="width: 60px; height: 60px; '
                'object-fit: cover; border-radius: 5px;" />',
                obj.featured_image.url,
            )
        return format_html(
            '<span style="color: #999;">بدون تصویر</span>'
        )

    featured_image_thumbnail.short_description = "تصویر شاخص"

    def reading_time_display(self, obj):
        """
        Returns the reading time with Persian digits and unit.
        """
        persian_digits = str(obj.reading_time).translate(
            str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        )
        return format_html(
            '<span style="font-size: 0.9em;">{} دقیقه</span>',
            persian_digits,
        )

    reading_time_display.short_description = "زمان مطالعه"
    reading_time_display.admin_order_field = "reading_time"

    def publication_status(self, obj):
        """
        Returns the publication status with color coding.
        """
        now = timezone.now()

        if not obj.is_published:
            badge_color = "#6E756F"
            badge_text = "پیش‌نویس"
        elif obj.published_at and obj.published_at > now:
            badge_color = "#E87932"
            badge_text = "زمان‌بندی شده"
        else:
            badge_color = "#245C43"
            badge_text = "منتشر شده"

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 4px 10px; border-radius: 12px; '
            'font-size: 0.85em;">{}</span>',
            badge_color,
            badge_text,
        )

    publication_status.short_description = "وضعیت انتشار"

    def tags_list(self, obj):
        """
        Returns formatted tags list.
        """
        tags = obj.tags.all()
        if not tags:
            return format_html(
                '<span style="color: #999;">بدون برچسب</span>'
            )

        tag_html = []
        for tag in tags[:5]:
            tag_html.append(
                format_html(
                    '<span style="background-color: #A8C66C; color: #173D2D; '
                    'padding: 2px 8px; border-radius: 10px; '
                    'font-size: 0.8em; margin: 2px;">{}</span>',
                    tag.name,
                )
            )

        if tags.count() > 5:
            tag_html.append(
                format_html(
                    '<span style="color: #666; font-size: 0.8em;">+{} بیشتر</span>',
                    tags.count() - 5,
                )
            )

        return format_html('<div style="line-height: 2;">{}</div>',
                          format_html(" ".join(str(t) for t in tag_html)))

    tags_list.short_description = "برچسب‌ها"

    def published_at_display(self, obj):
        """
        Returns publication date in a readable format.
        """
        if not obj.published_at:
            return format_html(
                '<span style="color: #999;">تعیین نشده</span>'
            )

        return obj.published_at.strftime("%Y/%m/%d %H:%M")

    published_at_display.short_description = "تاریخ انتشار"
    published_at_display.admin_order_field = "published_at"

    def updated_at_display(self, obj):
        """
        Returns last update date.
        """
        return obj.updated_at.strftime("%Y/%m/%d %H:%M")

    updated_at_display.short_description = "آخرین به‌روزرسانی"
    updated_at_display.admin_order_field = "updated_at"

    # ============================================================
    # Custom Actions
    # ============================================================

    @admin.action(description="انتشار مقالات انتخاب شده")
    def make_published(self, request, queryset):
        """
        Marks selected articles as published.
        """
        updated = queryset.update(
            is_published=True,
            published_at=timezone.now(),
        )
        self.message_user(
            request,
            f"{updated} مقاله با موفقیت منتشر شد.",
        )

    @admin.action(description="تبدیل به پیش‌نویس")
    def make_draft(self, request, queryset):
        """
        Marks selected articles as drafts.
        """
        updated = queryset.update(
            is_published=False,
            published_at=None,
        )
        self.message_user(
            request,
            f"{updated} مقاله به پیش‌نویس تبدیل شد.",
        )

    @admin.action(description="کپی مقالات انتخاب شده")
    def duplicate_articles(self, request, queryset):
        """
        Creates copies of selected articles.
        """
        created_count = 0
        for article in queryset:
            article.pk = None
            article.slug = f"{article.slug}-copy-{created_count}"
            article.title = f"{article.title} (کپی)"
            article.is_published = False
            article.published_at = None
            article.save()
            created_count += 1

        self.message_user(
            request,
            f"{created_count} مقاله کپی شد.",
        )

    # ============================================================
    # Form Customization
    # ============================================================

    def get_form(self, request, obj=None, **kwargs):
        """
        Returns the form with custom initial values.
        """
        form = super().get_form(request, obj, **kwargs)

        if not obj:
            form.base_fields["reading_time"].initial = 5
            form.base_fields["robots"].initial = "index,follow"

        return form

    def save_model(self, request, obj, form, change):
        """
        Handles special save logic for articles.
        """
        if not obj.slug:
            obj.slug = obj.title

        if obj.is_published and not obj.published_at:
            obj.published_at = timezone.now()

        super().save_model(request, obj, form, change)


# ============================================================
# Tag Admin Configuration
# ============================================================

# Unregister the default Tag admin from django-taggit
admin.site.unregister(Tag)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """
    Admin interface for managing tags.
    """

    list_display = ["name", "slug", "article_count"]
    search_fields = ["name", "slug"]
    list_per_page = 50

    def article_count(self, obj):
        """
        Returns the number of articles using this tag.
        """
        return obj.taggit_taggeditem_items.count()

    article_count.short_description = "تعداد مقالات"

    def get_queryset(self, request):
        """
        Optimizes queryset for tag listing.
        """
        return super().get_queryset(request).prefetch_related(
            "taggit_taggeditem_items"
        )