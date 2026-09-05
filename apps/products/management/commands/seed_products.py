import random
from io import BytesIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from faker import Faker
from PIL import Image, ImageDraw, ImageFont

from apps.products.models import Category, Product

User = get_user_model()
fake = Faker('fa_IR')

# Base product names per category keyword. Falls back to the category's own
# name when no keyword matches.
PRODUCT_NAME_MAP = {
    'پوست کن': ['پوست کن تیغه آلمانی', 'پوست کن طرح ترک', 'پوست کن معمولی'],
    'چاقو تیزکن': ['چاقو تیزکن جدید', 'چاقو تیزکن حرفه‌ای'],
    'جا ادویه': ['جا ادویه سه حالته', 'جا ادویه گردان'],
    'گلدان': ['گلدان استوانه‌ای', 'گلدان آجری', 'گلدان کاکتوسی'],
    'سردوش': ['سردوش گرد', 'سردوش مربعی', 'سردوش تلفنی'],
    'سیفون': ['سیفون فانتزی', 'سیفون کلاسیک', 'سیفون کششی'],
    'پیچ': ['پیچ چهارسو', 'پیچ دوسو', 'پیچ آلن'],
    'رولپلاک': ['رولپلاک لبه دار', 'رولپلاک شاخک دار'],
}

MATERIALS = ['پلاستیک فشرده', 'استیل ضد زنگ', 'آلومینیوم', 'پلی‌اتیلن', 'ABS']
FEATURES = [
    'کیفیت بالا', 'طراحی ارگونومیک', 'دوام طولانی',
    'نصب آسان', 'مناسب مصارف خانگی', 'بسته‌بندی استاندارد',
]
EXTRA_TAGS = ['کیفیت بالا', 'ارسال سریع', 'عمده فروشی', 'ضمانت', 'جدید']

PLACEHOLDER_COLORS = [
    (200, 200, 200),  # gray
    (180, 200, 180),  # light green
    (200, 180, 160),  # light brown
    (160, 180, 200),  # light blue
    (200, 160, 160),  # light red
]

FONT_CANDIDATES = [
    'C:/Windows/Fonts/IRANSans.ttf',
    'C:/Windows/Fonts/B-NAZANIN.TTF',
    'C:/Windows/Fonts/ARIAL.TTF',
]


class Command(BaseCommand):
    help = 'Generate mock products using the existing categories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=200,
            help='Number of products to create (default: 200)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete previously generated products first'
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Only create products under this category name'
        )

    def handle(self, *args, **options):
        count = options['count']

        if options['clear']:
            self.clear_products()

        if not Category.objects.exists():
            self.stdout.write(self.style.ERROR('❌ No categories found!'))
            self.stdout.write('Run this first:')
            self.stdout.write('  python manage.py seed_categories')
            return

        main_categories = Category.objects.filter(parent__isnull=True)

        if options['category']:
            main_categories = main_categories.filter(name__icontains=options['category'])
            if not main_categories.exists():
                self.stdout.write(self.style.ERROR(f'❌ Category "{options["category"]}" not found'))
                return

        self.stdout.write(f'🏭  Generating {count} products...')

        # Preload existing names so freshly generated ones never collide with
        # rows already in the database (Product.name has a unique constraint).
        self.used_names = set(Product.objects.values_list('name', flat=True))
        self.font = self.load_font()

        products = self.create_products(count, list(main_categories))

        self.print_summary(products)

    def get_admin_user(self):
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
        return admin

    def get_category_weights(self, main_categories):
        """Weight 'گلدان' (flower pots) at 35%, splitting the rest evenly."""
        others = [c for c in main_categories if 'گلدان' not in c.name]
        other_weight = 65 / len(others) if others else 0
        return [35 if 'گلدان' in c.name else other_weight for c in main_categories]

    def create_products(self, count, main_categories):
        admin = self.get_admin_user()
        weights = self.get_category_weights(main_categories)
        products = []

        for i in range(count):
            main_cat = random.choices(main_categories, weights=weights)[0]
            category = self.get_random_category(main_cat)
            name = self.get_unique_product_name(category)
            price, on_sale_price, call_for_price = self.get_pricing()

            product = Product(
                name=name,
                description=self.get_realistic_description(name, category),
                price=price,
                on_sale_price=on_sale_price,
                call_for_price=call_for_price,
                published=random.random() < 0.9,
                featured_in_special_sales=random.random() < 0.25,
                is_featured=random.random() < 0.15,
                featured_order=random.randint(1, 100) if random.random() < 0.15 else 0,
                creator=admin,
                category=category,
            )

            image_content = self.create_placeholder_image(name)
            product.cover_image.save(
                f'product_{i}_{random.randint(1000, 9999)}.jpg',
                image_content,
                save=False
            )

            product.save()
            product.tags.add(*self.get_tags(category))
            products.append(product)

            if (i + 1) % 25 == 0:
                self.stdout.write(f'  ⏳ {i + 1}/{count} products created...')

        return products

    def load_font(self, size=36):
        """Resolve the Persian font once and reuse it for every placeholder image."""
        for font_path in FONT_CANDIDATES:
            if Path(font_path).exists():
                return ImageFont.truetype(font_path, size)
        return ImageFont.load_default()

    def create_placeholder_image(self, name, width=800, height=600):
        """Build a simple placeholder image with Pillow."""
        bg_color = random.choice(PLACEHOLDER_COLORS)

        img = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        margin = 50
        draw.rectangle(
            [margin, margin, width - margin, height - margin],
            outline=(100, 100, 100),
            width=3
        )

        try:
            bbox = draw.textbbox((0, 0), name, font=self.font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            x = (width - text_width) / 2
            y = (height - text_height) / 2

            draw.text((x, y), name, fill=(50, 50, 50), font=self.font)
        except Exception:
            # Font can't render this text (missing glyphs, etc.) - keep the plain rectangle.
            pass

        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)

        return ContentFile(buffer.read())

    def get_random_category(self, main_cat):
        """Pick a category at a random depth (to exercise nested categories)."""
        # 40% depth 1, 35% depth 2, 20% depth 3, 5% depth 4
        depth = random.choices([1, 2, 3, 4], weights=[40, 35, 20, 5])[0]

        current = main_cat
        for _ in range(depth - 1):
            children = list(current.children.all())
            if not children:
                break
            current = random.choice(children)

        return current

    def get_base_product_name(self, category):
        """Pick a realistic base name for the category, falling back to the category name."""
        for key, names in PRODUCT_NAME_MAP.items():
            if key in category.name or category.name in key:
                return random.choice(names)
        return category.name

    def get_unique_product_name(self, category):
        """Generate a product name guaranteed not to collide with an existing one."""
        base = self.get_base_product_name(category)

        while True:
            # fake.unique never repeats a value within this process, so a
            # collision can only happen against a name from a previous run.
            suffix = fake.unique.random_int(min=1000, max=99999)
            candidate = f'{base} مدل {suffix}'
            if candidate not in self.used_names:
                self.used_names.add(candidate)
                return candidate

    def get_pricing(self):
        """Decide price and status."""
        # 15% call for price
        if random.random() < 0.15:
            return 0, None, True

        price = random.randint(50000, 5000000)

        # 30% on sale
        if random.random() < 0.30:
            on_sale = int(price * random.uniform(0.7, 0.9))
            return price, on_sale, False

        return price, None, False

    def get_realistic_description(self, name, category):
        return (
            f'{name} از جنس {random.choice(MATERIALS)}. '
            f'دارای {random.choice(FEATURES)} و {random.choice(FEATURES)}. '
            f'مناسب {category.name}.'
        )

    def get_tags(self, category):
        tags = [category.name]

        parent = category.parent
        while parent:
            tags.append(parent.name)
            parent = parent.parent

        tags.extend(random.sample(EXTRA_TAGS, k=2))
        return tags

    def clear_products(self):
        self.stdout.write('🗑️  Deleting existing products...')
        count = Product.objects.count()
        Product.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'✅ Deleted {count} products'))

    def print_summary(self, products):
        total = len(products)
        published = sum(1 for p in products if p.published)
        sale = sum(1 for p in products if p.on_sale_price)
        call_price = sum(1 for p in products if p.call_for_price)
        featured = sum(1 for p in products if p.featured_in_special_sales)

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('📊 Summary:')
        self.stdout.write(f'  🎯 Total products: {total}')
        self.stdout.write(f'  ✅ Published: {published}')
        self.stdout.write(f'  💰 On sale: {sale}')
        self.stdout.write(f'  📞 Call for price: {call_price}')
        self.stdout.write(f'  ⭐ Featured: {featured}')
        self.stdout.write('=' * 50 + '\n')
