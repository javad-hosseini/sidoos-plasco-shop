from django.contrib import admin
from django.utils.html import format_html

from .models import HeroSlide


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
