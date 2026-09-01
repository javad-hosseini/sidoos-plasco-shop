from django.db import models
from django.core.validators import MinValueValidator
from django.utils.text import slugify
from taggit.managers import TaggableManager
from django.conf import settings
from django_ckeditor_5.fields import CKEditor5Field


class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='product_categories_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['parent', 'name'], name='unique_category_name_per_parent'),
        ]
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['parent']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or 'category'
            candidate = base_slug
            suffix = 2

            while Category.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f'{base_slug}-{suffix}'
                suffix += 1

            self.slug = candidate

        super().save(*args, **kwargs)

    def get_descendant_ids(self):
        descendant_ids = [self.id]
        frontier_ids = [self.id]

        while frontier_ids:
            children_ids = list(
                Category.objects.filter(parent_id__in=frontier_ids).values_list('id', flat=True)
            )
            if not children_ids:
                break

            descendant_ids.extend(children_ids)
            frontier_ids = children_ids

        return descendant_ids

    def __str__(self):
        if self.parent:
            return f'{self.parent} / {self.name}'
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True, allow_unicode=True)
    description = CKEditor5Field(help_text="Product description with rich text formatting")

    # Pricing
    price = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="Regular price of the product in Toman"
    )
    on_sale_price = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Sale price in Toman (optional). If set, discount % is calculated automatically"
    )
    
    # Media
    cover_image = models.ImageField(
        upload_to='products/covers/',
        help_text="Main cover image for the product"
    )
    
    # Flags/Status
    call_for_price = models.BooleanField(
        default=False,
        help_text="If checked, price will be hidden and displayed as 'Call for price'. Price stored internally as 0."
    )
    published = models.BooleanField(
        default=False,
        help_text="Uncheck to hide product from website"
    )
    featured_in_special_sales = models.BooleanField(
        default=False,
        help_text="Include in 'Special Sales' section of website"
    )
    
    # Relations
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products_created'
    )
    tags = TaggableManager(blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['published']),
            models.Index(fields=['featured_in_special_sales']),
            models.Index(fields=['slug']),
        ]
    
    def save(self, *args, **kwargs):
        # Auto-generate a unique slug when not provided.
        if not self.slug:
            base_slug = slugify(self.name, allow_unicode=True) or 'product'
            candidate = base_slug
            suffix = 2

            while Product.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f'{base_slug}-{suffix}'
                suffix += 1

            self.slug = candidate
        
        # If call_for_price is True, set price to 0
        if self.call_for_price:
            self.price = 0
        
        super().save(*args, **kwargs)
    
    def get_discount_percentage(self):
        """Calculate discount percentage if on_sale_price is set."""
        if self.on_sale_price and self.price and self.price > 0:
            discount = ((self.price - self.on_sale_price) / self.price) * 100
            return round(discount, 2)
        return None
    
    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='products/images/')
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"Image for {self.product.name}"


class ProductSave(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_products'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='saved_by_users'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'product')
        verbose_name_plural = "Product Saves"
    
    def __str__(self):
        return f"{self.user.username} saved {self.product.name}"


class ProductLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='liked_products'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='liked_by_users'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'product')
        verbose_name_plural = "Product Likes"
    
    def __str__(self):
        return f"{self.user.username} liked {self.product.name}"
