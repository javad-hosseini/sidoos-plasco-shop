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
    readonly_fields = ('slug', 'created_at', 'updated_at', 'discount_percentage')
    autocomplete_fields = ('category', 'creator')

    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('name', 'slug', 'description')
        }),
        ('تصویر شاخص', {
            'fields': ('cover_image',)
        }),
        ('قیمت‌گذاری', {
            'fields': ('price', 'on_sale_price', 'call_for_price', 'discount_percentage'),
            'description': 'برای پنهان کردن قیمت و نمایش «تماس بگیرید»، «تماس برای قیمت» را فعال کنید. درصد تخفیف به‌طور خودکار محاسبه می‌شود.'
        }),
        ('بهینه‌سازی موتور جستجو (SEO)', {
            'fields': ('meta_title', 'meta_description', 'og_image', 'canonical_url'),
            'description': 'این فیلدها برای بهبود رتبه در گوگل و شبکه‌های اجتماعی استفاده می‌شوند. در صورت خالی بودن، مقادیر پیش‌فرض (نام محصول) استفاده خواهد شد.'
        }),
        ('وضعیت و نمایش', {
            'fields': (
                'published',
                'featured_in_special_sales',
                'is_featured',
                'featured_order',
            )
        }),
        ('دسته‌بندی، برچسب‌ها و ایجادکننده', {
            'fields': ('category', 'tags', 'creator')
        }),
        ('زمان‌بندی', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [ProductImageInline]

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
    readonly_fields = ('slug', 'created_at', 'updated_at')
    fields = ('name', 'slug', 'parent', 'creator', 'created_at', 'updated_at')
    autocomplete_fields = ('parent',)


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