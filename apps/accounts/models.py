from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        blank=True,
        null=True,
        verbose_name="شماره موبایل",
        help_text="شماره موبایل کاربر، مثلاً 09123456789. اگر پر شود، باید برای هر کاربر منحصربه‌فرد باشد.",
    )

    # در حال حاضر همه‌ی کاربران این دسترسی را دارند؛ این فیلد برای کنترل دقیق‌تر در آینده نگه داشته شده است.
    has_price_access = models.BooleanField(
        default=True,
        verbose_name="دسترسی به مشاهده قیمت",
        help_text="اگر غیرفعال شود، این کاربر باوجود ورود به حساب کاربری، به‌جای قیمت واقعی محصولات فقط پیام «قیمت ویژه‌ی حساب‌های تأییدشده» را می‌بیند.",
    )

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self):
        return self.username