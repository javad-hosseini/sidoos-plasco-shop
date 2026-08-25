from django.contrib import admin
from django.utils.html import format_html
from .models import Product, ProductImage, ProductSave, ProductLike


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ('image', 'order')
    ordering = ('order', 'created_at')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'price_display',
        'discount_display',
        'call_for_price',
        'published',
        'featured_in_special_sales',
        'created_at'
    )
    list_filter = (
        'published',
        'featured_in_special_sales',
        'call_for_price',
        'created_at'
    )
    search_fields = ('name', 'description')
    readonly_fields = ('slug', 'created_at', 'updated_at', 'discount_percentage')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Media', {
            'fields': ('cover_image',)
        }),
        ('Pricing', {
            'fields': ('price', 'on_sale_price', 'call_for_price', 'discount_percentage'),
            'description': 'Set call_for_price to hide actual price. Discount % is auto-calculated.'
        }),
        ('Status & Visibility', {
            'fields': ('published', 'featured_in_special_sales')
        }),
        ('Tags & Creator', {
            'fields': ('tags', 'creator')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ProductImageInline]
    
    def price_display(self, obj):
        if obj.call_for_price:
            return format_html('<span style="color: red;">Call for Price</span>')
        return f"${obj.price}"
    price_display.short_description = 'Price'
    
    def discount_display(self, obj):
        discount = obj.get_discount_percentage()
        if discount:
            return format_html(
                '<span style="color: green; font-weight: bold;">{}%</span>',
                f'{discount:.1f}'
            )
        return '-'
    discount_display.short_description = 'Sale Discount %'
    
    def discount_percentage(self, obj):
        discount = obj.get_discount_percentage()
        return f"{discount}%" if discount else "No sale price set"
    discount_percentage.short_description = 'Discount Percentage'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'order', 'created_at', 'image_preview')
    list_filter = ('created_at', 'product')
    search_fields = ('product__name',)
    ordering = ('product', 'order')
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover;"/>',
                obj.image.url
            )
        return 'No image'
    image_preview.short_description = 'Preview'


@admin.register(ProductSave)
class ProductSaveAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('user__username', 'product__name')
    readonly_fields = ('created_at',)
    
    def has_add_permission(self, request):
        # Saves should be created via frontend, not admin
        return False


@admin.register(ProductLike)
class ProductLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('user__username', 'product__name')
    readonly_fields = ('created_at',)
    
    def has_add_permission(self, request):
        # Likes should be created via frontend, not admin
        return False
