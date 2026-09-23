from django import forms
from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, ProductImage, ProductSave, ProductLike


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ('image', 'order')
    ordering = ('order', 'created_at')
    verbose_name = "تصویر گالری"
    verbose_name_plural = "تصاویر گالری"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'price_display',
        'discount_display',
        'call_for_price',
        'published',
        'featured_in_special_sales',
        'is_featured',
        'featured_order',
        'category',
        'meta_title',          # SEO title
        'meta_description',    # <-- FIXED: Now in list_display
        'canonical_url',       # <-- FIXED: Now in list_display
        'created_at'
    )
    list_editable = (
        'is_featured',
        'featured_order',
        'meta_title',          # Bulk-edit SEO titles
        'meta_description',    # Bulk-edit meta descriptions
        'canonical_url',       # Bulk-edit canonical URLs
    )
    list_filter = (
        'published',
        'featured_in_special_sales',
        'is_featured',
        'category',
        'call_for_price',
        'created_at'
    )
    search_fields = (
        'name',
        'description',
        'meta_title',
        'meta_description',
    )
    readonly_fields = ('created_at', 'updated_at', 'discount_percentage', 'canonical_preview')
    prepopulated_fields = {'slug': ('name',)}

    class Media:
        js = ('admin/js/auto_prepopulate_seo.js',)

    fieldsets = (
        ('اطلاعات پایه و دسته‌بندی', {
            'fields': ('name', 'slug', 'category', 'creator', 'description', 'tags'),
            'description': 'اطلاعات اصلی، دسته‌بندی، ثبت‌کننده محصول و برچسب‌های مرتبط.'
        }),
        ('تصویر شاخص', {
            'fields': ('cover_image',)
        }),
        ('قیمت‌گذاری', {
            'fields': ('price', 'on_sale_price', 'call_for_price', 'discount_percentage'),
            'description': 'برای پنهان کردن قیمت و نمایش «تماس بگیرید»، «تماس برای قیمت» را فعال کنید. درصد تخفیف به‌طور خودکار محاسبه می‌شود.'
        }),
        ('بهینه‌سازی موتور جستجو (SEO)', {
            'fields': ('meta_title', 'meta_description', 'og_image', 'canonical_preview', 'canonical_url'),
            'description': 'در صورت خالی گذاشتن، عنوان و توضیحات سئو به صورت خودکار از نام و توضیحات محصول تولید می‌شوند.'
        }),
        ('وضعیت و نمایش', {
            'fields': (
                'published',
                'featured_in_special_sales',
                'is_featured',
                'featured_order',
            )
        }),
        ('زمان‌بندی', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [ProductImageInline]

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if "creator" not in initial:
            initial["creator"] = request.user.pk
        if "featured_order" not in initial:
            initial["featured_order"] = 2
        return initial

    def save_model(self, request, obj, form, change):
        if not obj.creator_id:
            obj.creator = request.user
        super().save_model(request, obj, form, change)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "canonical_url":
            kwargs["widget"] = forms.TextInput(
                attrs={
                    "placeholder": "برای استفاده از آدرس خودکار بالا خالی بگذارید، یا آدرس جدید را وارد کنید (مانند /products/...)",
                    "style": "width: 100%; max-width: 650px; direction: ltr; text-align: left;",
                }
            )
        elif db_field.name == "meta_title":
            kwargs["widget"] = forms.TextInput(
                attrs={
                    "placeholder": "پیش‌فرض خودکار: [نام محصول] | سیدوس",
                    "style": "width: 100%; max-width: 650px;",
                }
            )
        elif db_field.name == "meta_description":
            kwargs["widget"] = forms.Textarea(
                attrs={
                    "placeholder": "پیش‌فرض خودکار: برگرفته از توضیحات محصول (حداکثر ۱۶۰ کاراکتر)",
                    "rows": 3,
                    "style": "width: 100%; max-width: 650px;",
                }
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @admin.display(description="آدرس Canonical فعال (پیش‌نمایش خودکار)")
    def canonical_preview(self, obj):
        if not obj or not obj.pk:
            return format_html(
                '<div style="background: rgba(13,110,253,0.06); border: 1px dashed #0d6efd; border-radius: 6px; padding: 8px 12px; font-size: 13px; color: #495057;">'
                'ℹ️ <strong>راهنما:</strong> پس از ذخیره اولیه محصول، آدرس اختصاصی پیش‌فرض سیستم (<code>https://sidoos.ir/products/اسلاگ/</code>) به صورت خودکار ایجاد و فعال می‌شود. '
                'اگر می‌خواهید از همین آدرس پیش‌فرض استفاده شود، <strong>کادر «آدرس canonical» زیر را خالی بگذارید</strong>.'
                '</div>'
            )
        default_url = obj.get_default_canonical_url()
        if obj.canonical_url:
            return format_html(
                '<div style="background: rgba(255,193,7,0.12); border: 1px solid rgba(255,193,7,0.4); border-radius: 6px; padding: 10px 14px; margin-bottom: 6px;">'
                '<span style="display:inline-block; padding:3px 9px; border-radius:4px; font-weight:bold; font-size:11px; background:#ffc107; color:#000; margin-bottom:6px;">⚠️ آدرس سفارشی دستی (توسط شما وارد شده)</span><br>'
                '<strong>آدرس Canonical فعال در سایت:</strong> <a href="{0}" target="_blank" style="direction:ltr; text-align:left; display:inline-block; word-break:break-all; font-family:monospace; font-weight:bold; color:#0d6efd; margin: 4px 0;">{0}</a><br>'
                '<span style="color:#6c757d; font-size:12px;">آدرس پیش‌فرض خودکار سیستم در صورت خالی کردن کادر زیر: <span style="direction:ltr; display:inline-block; font-family:monospace;">{1}</span></span>'
                '</div>',
                obj.canonical_url,
                default_url
            )
        return format_html(
            '<div style="background: rgba(255,193,7,0.12); border: 1px solid rgba(25,135,84,0.3); border-radius: 6px; padding: 10px 14px; margin-bottom: 6px; background-color: rgba(25,135,84,0.08);">'
            '<span style="display:inline-block; padding:3px 9px; border-radius:4px; font-weight:bold; font-size:11px; background:#198754; color:#fff; margin-bottom:6px;">✅ آدرس خودکار سیستم (فعال)</span><br>'
            '<strong>آدرس Canonical فعال در سایت:</strong> <a href="{0}" target="_blank" style="direction:ltr; text-align:left; display:inline-block; word-break:break-all; font-family:monospace; font-weight:bold; color:#0d6efd; margin: 4px 0;">{0}</a><br>'
            '<span style="color:#6c757d; font-size:12px;">💡 این آدرس بر اساس اسلاگ محصول تولید شده و به طور پیش‌فرض استفاده می‌شود. تنها در صورتی که تصمیم به تغییر آن دارید، کادر زیر را پر کنید.</span>'
            '</div>',
            default_url
        )

    def price_display(self, obj):
        if obj.call_for_price:
            return format_html('<span style="color: red;">تماس بگیرید</span>')
        return f"{obj.price:,} تومان"
    price_display.short_description = 'قیمت'

    def discount_display(self, obj):
        discount = obj.get_discount_percentage()
        if discount:
            return format_html(
                '<span style="color: green; font-weight: bold;">{}٪</span>',
                f'{discount:.1f}'
            )
        return '-'
    discount_display.short_description = 'درصد تخفیف'

    def discount_percentage(self, obj):
        discount = obj.get_discount_percentage()
        return f"{discount}٪" if discount else "بدون قیمت تخفیف‌دار"
    discount_percentage.short_description = 'درصد تخفیف'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'creator', 'created_at')
    list_filter = ('parent', 'created_at')
    search_fields = ('name', 'parent__name', 'creator__username')
    readonly_fields = ('created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    fields = ('name', 'slug', 'parent', 'creator', 'created_at', 'updated_at')

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if "creator" not in initial:
            initial["creator"] = request.user.pk
        return initial

    def save_model(self, request, obj, form, change):
        if not obj.creator_id:
            obj.creator = request.user
        super().save_model(request, obj, form, change)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'order', 'created_at', 'image_preview')
    list_filter = ('created_at', 'product')
    search_fields = ('product__name',)
    ordering = ('product', 'order')
    autocomplete_fields = ('product',)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover;"/>',
                obj.image.url
            )
        return 'بدون تصویر'
    image_preview.short_description = 'پیش‌نمایش'


@admin.register(ProductSave)
class ProductSaveAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('user__username', 'product__name')
    readonly_fields = ('created_at',)

    def has_add_permission(self, request):
        return False


@admin.register(ProductLike)
class ProductLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('user__username', 'product__name')
    readonly_fields = ('created_at',)

    def has_add_permission(self, request):
        return False