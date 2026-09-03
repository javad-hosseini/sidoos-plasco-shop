from django.core.management.base import BaseCommand

from apps.products.models import Category, Product, ProductImage, ProductLike, ProductSave


class Command(BaseCommand):
    help = 'پاک کردن تمام داده‌های mock از دیتابیس'

    def handle(self, *args, **options):
        self.stdout.write('🗑️  در حال پاک کردن تمام محصولات و دسته‌بندی‌ها...')

        # پاک کردن وابستگی‌ها
        ProductLike.objects.all().delete()
        ProductSave.objects.all().delete()
        ProductImage.objects.all().delete()

        # پاک کردن محصولات و دسته‌ها
        product_count = Product.objects.count()
        category_count = Category.objects.count()

        Product.objects.all().delete()
        Category.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            f'✅ {product_count} محصول و {category_count} دسته‌بندی پاک شد'
        ))