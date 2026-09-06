from django.core.management.base import BaseCommand

from apps.products.models import Category, Product, ProductImage, ProductLike, ProductSave


class Command(BaseCommand):
    help = 'Delete all mock data from the database'

    def handle(self, *args, **options):
        self.stdout.write('🗑️  Deleting all products and categories...')

        # Delete dependent rows first
        ProductLike.objects.all().delete()
        ProductSave.objects.all().delete()
        ProductImage.objects.all().delete()

        # Delete products and categories
        product_count = Product.objects.count()
        category_count = Category.objects.count()

        Product.objects.all().delete()
        Category.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            f'✅ Deleted {product_count} products and {category_count} categories'
        ))