from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.text import slugify
from taggit.managers import TaggableManager
from django.conf import settings
from django_ckeditor_5.fields import CKEditor5Field


class Category(models.Model):
    name = models.CharField(
        max_length=255,
        verbose_name="نام",
        help_text="نام دسته‌بندی، مثلاً «گلدان» یا «ابزارآلات آشپزخانه». در فروشگاه و در فهرست دسته‌بندی‌ها نمایش داده می‌شود.",
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        allow_unicode=True,
        verbose_name="اسلاگ (شناسه URL)",
        help_text="بخشی از آدرس این دسته‌بندی در سایت. اگر خالی بگذارید، به‌طور خودکار از روی نام ساخته می‌شود.",
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="دسته‌بندی والد",
        help_text="اگر این دسته‌بندی زیرمجموعه‌ی دسته‌بندی دیگری است، آن را اینجا انتخاب کنید. برای دسته‌بندی‌های اصلی (سطح اول)، این فیلد را خالی بگذارید.",
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='product_categories_created',
        verbose_name="ایجادکننده",
        help_text="کاربری که این دسته‌بندی را ایجاد کرده است.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد",
        help_text="تاریخ و زمان ایجاد این دسته‌بندی (به‌صورت خودکار ثبت می‌شود).",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاریخ به‌روزرسانی",
        help_text="تاریخ و زمان آخرین ویرایش این دسته‌بندی (به‌صورت خودکار ثبت می‌شود).",
    )

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['parent', 'name'], name='unique_category_name_per_parent'),
        ]
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['parent']),
        ]

    def save(self, *args, **kwargs):
        # allow_unicode=True so Persian category names produce a readable
        # slug instead of slugify() silently stripping all non-ASCII text
        # (which is what Product.save() already does correctly below).
        if not self.slug:
            base_slug = slugify(self.name, allow_unicode=True) or 'category'
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

    def get_ancestors(self, include_self=False):
        """Return this category's chain from the root down to itself (or its parent), for breadcrumbs."""
        chain = []
        node = self if include_self else self.parent

        while node:
            chain.append(node)
            node = node.parent

        chain.reverse()
        return chain

    def __str__(self):
        if self.parent:
            return f'{self.parent} / {self.name}'
        return self.name


class Product(models.Model):
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="نام محصول",
        help_text="نام محصول همان‌طور که در فروشگاه نمایش داده می‌شود. باید یکتا باشد؛ دو محصول نمی‌توانند نام یکسان داشته باشند.",
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        allow_unicode=True,
        verbose_name="اسلاگ (شناسه URL)",
        help_text="بخشی از آدرس این محصول در سایت. اگر خالی بگذارید، به‌طور خودکار از روی نام ساخته می‌شود.",
    )
    description = CKEditor5Field(
        verbose_name="توضیحات",
        help_text="توضیحات کامل محصول. می‌توانید از قالب‌بندی متن (پررنگ، لیست، تصویر و غیره) استفاده کنید؛ این متن در صفحه اختصاصی محصول نمایش داده می‌شود.",
    )

    # Pricing
    price = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="قیمت (تومان)",
        help_text="قیمت عادی محصول به تومان و بدون جداکننده هزارگان (مثلاً برای دویست هزار تومان عدد 200000 را وارد کنید). اگر «تماس برای قیمت» فعال باشد، این مقدار نادیده گرفته و صفر ذخیره می‌شود.",
    )
    on_sale_price = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="قیمت با تخفیف (تومان)",
        help_text="قیمت محصول در زمان تخفیف (اختیاری). اگر مقداری وارد کنید، درصد تخفیف به‌طور خودکار محاسبه و در سایت نمایش داده می‌شود. باید کمتر یا مساوی «قیمت» باشد.",
    )

    # Media
    cover_image = models.ImageField(
        upload_to='products/covers/',
        verbose_name="تصویر شاخص",
        help_text="تصویر اصلی محصول که در فهرست محصولات و بالای صفحه اختصاصی آن نمایش داده می‌شود. تصویر روشن و باکیفیت انتخاب کنید.",
    )

    # Flags/Status
    call_for_price = models.BooleanField(
        default=False,
        verbose_name="تماس برای قیمت",
        help_text="در صورت فعال بودن، به‌جای قیمت به مشتری عبارت «تماس بگیرید» نمایش داده می‌شود و فیلدهای قیمت و قیمت با تخفیف غیرفعال می‌شوند. برای محصولاتی که قیمت ثابتی ندارند مناسب است.",
    )
    published = models.BooleanField(
        default=False,
        verbose_name="منتشر شده",
        help_text="در صورت غیرفعال بودن، این محصول در فروشگاه نمایش داده نمی‌شود اما در پنل مدیریت باقی می‌ماند؛ برای پیش‌نویس کردن محصولات ناتمام مناسب است.",
    )
    featured_in_special_sales = models.BooleanField(
        default=False,
        verbose_name="فروش ویژه",
        help_text="در صورت فعال بودن، این محصول واجد شرایط نمایش در بخش «فروش ویژه» سایت می‌شود. برای نمایش واقعی در صفحه اصلی، باید در بخش «محصولات فروش ویژه» پنل صفحه اصلی نیز انتخاب شود.",
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name="محصول ویژه",
        help_text="نمایش در بخش «محصولات منتخب» صفحه اصلی"
    )
    featured_order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش ویژه",
        help_text="ترتیب نمایش در «محصولات منتخب» صفحه اصلی (کوچک‌تر = جلوتر)"
    )

    # Relations
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products_created',
        verbose_name="ایجادکننده",
        help_text="کاربری که این محصول را در پنل مدیریت ثبت کرده است.",
    )
    tags = TaggableManager(
        blank=True,
        verbose_name="برچسب‌ها",
        help_text="برچسب‌های مرتبط با این محصول برای جست‌وجوی بهتر و نمایش محصولات مشابه.",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name="دسته‌بندی",
        help_text="دسته‌بندی‌ای که این محصول به آن تعلق دارد.",
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد",
        help_text="تاریخ و زمان ثبت این محصول (به‌صورت خودکار ثبت می‌شود).",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاریخ به‌روزرسانی",
        help_text="تاریخ و زمان آخرین ویرایش این محصول (به‌صورت خودکار ثبت می‌شود).",
    )

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['published']),
            models.Index(fields=['featured_in_special_sales']),
            models.Index(fields=['is_featured', 'featured_order']),
            models.Index(fields=['slug']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(on_sale_price__isnull=True) | models.Q(on_sale_price__lte=models.F('price')),
                name='product_sale_price_lte_price',
            ),
            models.CheckConstraint(
                check=models.Q(call_for_price=False) | (
                    models.Q(price=0) & models.Q(on_sale_price__isnull=True)
                ),
                name='product_call_for_price_invariants',
            ),
        ]
    
    def clean(self):
        super().clean()

        if self.call_for_price:
            # Call-for-price products have no public monetary price.
            self.price = 0
            if self.on_sale_price is not None:
                raise ValidationError({
                    'on_sale_price': 'برای محصول «تماس برای قیمت»، قیمت فروش ویژه نباید تعیین شود.'
                })

        if self.on_sale_price is not None and self.on_sale_price > self.price:
            raise ValidationError({
                'on_sale_price': 'قیمت فروش ویژه نمی‌تواند بیشتر از قیمت اصلی باشد.'
            })

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

        self.full_clean()
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
        related_name='images',
        verbose_name="محصول",
        help_text="محصولی که این تصویر به گالری آن تعلق دارد.",
    )
    image = models.ImageField(
        upload_to='products/images/',
        verbose_name="تصویر",
        help_text="یکی از تصاویر گالری این محصول (علاوه بر تصویر شاخص).",
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش",
        help_text="ترتیب نمایش این تصویر در گالری محصول (کوچک‌تر = جلوتر).",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ افزودن",
        help_text="تاریخ و زمان افزودن این تصویر (به‌صورت خودکار ثبت می‌شود).",
    )

    class Meta:
        verbose_name = "تصویر محصول"
        verbose_name_plural = "تصاویر محصول"
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"تصویر محصول «{self.product.name}»"


class ProductSave(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_products',
        verbose_name="کاربر",
        help_text="کاربری که این محصول را ذخیره کرده است.",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='saved_by_users',
        verbose_name="محصول",
        help_text="محصولی که ذخیره شده است.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ذخیره",
        help_text="تاریخ و زمان ذخیره این محصول توسط کاربر.",
    )

    class Meta:
        unique_together = ('user', 'product')
        verbose_name = "محصول ذخیره‌شده"
        verbose_name_plural = "محصولات ذخیره‌شده"

    def __str__(self):
        return f"{self.user.username} محصول «{self.product.name}» را ذخیره کرد"


class ProductLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='liked_products',
        verbose_name="کاربر",
        help_text="کاربری که این محصول را پسندیده است.",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='liked_by_users',
        verbose_name="محصول",
        help_text="محصولی که پسندیده شده است.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ پسندیدن",
        help_text="تاریخ و زمان پسندیدن این محصول توسط کاربر.",
    )

    class Meta:
        unique_together = ('user', 'product')
        verbose_name = "پسند محصول"
        verbose_name_plural = "پسندهای محصول"

    def __str__(self):
        return f"{self.user.username} محصول «{self.product.name}» را پسندید"
