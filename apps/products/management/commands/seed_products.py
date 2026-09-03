import random
from io import BytesIO

import requests
from PIL import Image, ImageDraw
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from faker import Faker

from apps.products.models import Category, Product

User = get_user_model()
fake = Faker('fa_IR')


class Command(BaseCommand):
    help = 'تولید محصولات mock با استفاده از دسته‌بندی‌های موجود'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=200,
            help='تعداد محصولات (پیش‌فرض: 200)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='پاک کردن محصولات mock قبلی'
        )
        parser.add_argument(
            '--category',
            type=str,
            help='فقط در این دسته‌بندی محصول بساز'
        )

    def handle(self, *args, **options):
        count = options['count']

        if options['clear']:
            self.clear_products()

        if not Category.objects.exists():
            self.stdout.write(self.style.ERROR('❌ هیچ دسته‌بندی‌ای وجود ندارد!'))
            self.stdout.write('ابتدا دستور زیر را اجرا کنید:')
            self.stdout.write('  python manage.py seed_categories')
            return

        main_categories = Category.objects.filter(parent__isnull=True)

        if options['category']:
            main_categories = main_categories.filter(name__icontains=options['category'])
            if not main_categories.exists():
                self.stdout.write(self.style.ERROR(f'❌ دسته‌بندی "{options["category"]}" یافت نشد'))
                return

        self.stdout.write(f'🏭  در حال تولید {count} محصول...')
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

    def create_products(self, count, main_categories):
        admin = self.get_admin_user()
        products = []

        weights = []
        for cat in main_categories:
            if 'گلدان' in cat.name:
                weights.append(35)
            else:
                weights.append(65 / (len(main_categories) - 1 if len(main_categories) > 1 else 1))

        for i in range(count):
            main_cat = random.choices(main_categories, weights=weights)[0]
            category = self.get_random_category(main_cat)
            name = self.get_product_name(category)
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

            # تولید تصویر placeholder
            image_content = self.create_placeholder_image(name)
            product.cover_image.save(
                f'product_{i}_{random.randint(1000, 9999)}.jpg',
                image_content,
                save=False
            )

            product.save()

            tags = self.get_tags(category)
            product.tags.add(*tags)

            products.append(product)

            if (i + 1) % 25 == 0:
                self.stdout.write(f'  ⏳ {i + 1}/{count} محصول ساخته شد...')

        return products

    def create_placeholder_image(self, name, width=800, height=600):
        """ساخت تصویر placeholder با Pillow"""
        # رنگ تصادفی پس‌زمینه
        colors = [
            (200, 200, 200),  # طوسی
            (180, 200, 180),  # سبز ملایم
            (200, 180, 160),  # قهوه‌ای ملایم
            (160, 180, 200),  # آبی ملایم
            (200, 160, 160),  # قرمز ملایم
        ]
        bg_color = random.choice(colors)

        # ساخت تصویر
        img = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        # رسم یک مستطیل وسط
        margin = 50
        draw.rectangle(
            [margin, margin, width - margin, height - margin],
            outline=(100, 100, 100),
            width=3
        )

        # نوشتن نام محصول (فارسی)
        try:
            # تلاش برای استفاده از فونت فارسی
            from pathlib import Path
            import glob

            # جستجوی فونت فارسی
            font_paths = [
                'C:/Windows/Fonts/IRANSans.ttf',
                'C:/Windows/Fonts/B-NAZANIN.TTF',
                'C:/Windows/Fonts/ARIAL.TTF',
            ]

            font = None
            for font_path in font_paths:
                if Path(font_path).exists():
                    from PIL import ImageFont
                    font = ImageFont.truetype(font_path, 36)
                    break

            if font is None:
                font = ImageFont.load_default()

            # موقعیت متن
            bbox = draw.textbbox((0, 0), name, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            x = (width - text_width) / 2
            y = (height - text_height) / 2

            draw.text((x, y), name, fill=(50, 50, 50), font=font)
        except:
            # اگر فونت فارسی نبود، فقط مستطیل رسم می‌شه
            pass

        # ذخیره در بافر
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)

        return ContentFile(buffer.read())

    def get_random_category(self, main_cat):
        """انتخاب دسته‌بندی با عمق تصادفی (برای تست تودرتو)"""
        # ۴۰٪ سطح ۱، ۳۵٪ سطح ۲، ۲۰٪ سطح ۳، ۵٪ سطح ۴
        depth = random.choices([1, 2, 3, 4], weights=[40, 35, 20, 5])[0]

        current = main_cat
        for d in range(depth - 1):
            children = list(current.children.all())
            if not children:
                break
            current = random.choice(children)

        return current

    def get_product_name(self, category, index=None):
        """تولید نام محصول بر اساس دسته‌بندی"""
        names_map = {
            'پوست کن': ['پوست کن تیغه آلمانی', 'پوست کن طرح ترک', 'پوست کن معمولی'],
            'چاقو تیزکن': ['چاقو تیزکن جدید', 'چاقو تیزکن حرفه‌ای'],
            'جا ادویه': ['جا ادویه سه حالته', 'جا ادویه گردان'],
            'گلدان': ['گلدان استوانه‌ای', 'گلدان آجری', 'گلدان کاکتوسی'],
            'سردوش': ['سردوش گرد', 'سردوش مربعی', 'سردوش تلفنی'],
            'سیفون': ['سیفون فانتزی', 'سیفون کلاسیک', 'سیفون کششی'],
            'پیچ': ['پیچ چهارسو', 'پیچ دوسو', 'پیچ آلن'],
            'رولپلاک': ['رولپلاک لبه دار', 'رولپلاک شاخک دار'],
        }

        for key, names in names_map.items():
            if key in category.name or category.name in key:
                base = random.choice(names)
                break
        else:
            base = category.name

        # ساخت نام یکتا
        if index is not None:
            return f'{base} مدل {index:03d}'

        return f'{base} مدل {random.randint(100, 999)}'

    def get_pricing(self):
        """تعیین قیمت و وضعیت"""
        # ۱۵٪ تماس بگیرید
        if random.random() < 0.15:
            return 0, None, True

        # قیمت عادی
        price = random.randint(50000, 5000000)

        # ۳۰٪ تخفیف
        if random.random() < 0.30:
            on_sale = int(price * random.uniform(0.7, 0.9))
            return price, on_sale, False

        return price, None, False

    def get_realistic_description(self, name, category):
        """تولید توضیح واقع‌گرایانه"""
        materials = ['پلاستیک فشرده', 'استیل ضد زنگ', 'آلومینیوم', 'پلی‌اتیلن', 'ABS']
        features = [
            'کیفیت بالا', 'طراحی ارگونومیک', 'دوام طولانی',
            'نصب آسان', 'مناسب مصارف خانگی', 'بسته‌بندی استاندارد',
        ]

        return (
            f'{name} از جنس {random.choice(materials)}. '
            f'دارای {random.choice(features)} و {random.choice(features)}. '
            f'مناسب {category.name}.'
        )

    def get_image_from_picsum(self, width=800, height=600):
        """دانلود تصویر از picsum.photos"""
        url = f'https://picsum.photos/{width}/{height}?random={random.randint(1, 1000)}'
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return ContentFile(response.content)
        except:
            pass
        return None

    def get_tags(self, category):
        """تولید تگ‌های مرتبط"""
        tags = [category.name]

        # تگ‌های والدین
        parent = category.parent
        while parent:
            tags.append(parent.name)
            parent = parent.parent

        # تگ‌های اضافی
        extra = ['کیفیت بالا', 'ارسال سریع', 'عمده فروشی', 'ضمانت', 'جدید']
        tags.extend(random.sample(extra, k=2))

        return tags

    def clear_products(self):
        """پاک کردن محصولات"""
        self.stdout.write('🗑️  در حال پاک کردن محصولات...')
        count = Product.objects.count()
        Product.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'✅ {count} محصول پاک شد'))

    def print_summary(self, products):
        """چاپ خلاصه"""
        total = len(products)
        published = sum(1 for p in products if p.published)
        sale = sum(1 for p in products if p.on_sale_price)
        call_price = sum(1 for p in products if p.call_for_price)
        featured = sum(1 for p in products if p.featured_in_special_sales)

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('📊 خلاصه تولید داده:')
        self.stdout.write(f'  🎯 کل محصولات: {total}')
        self.stdout.write(f'  ✅ منتشر شده: {published}')
        self.stdout.write(f'  💰 تخفیف‌دار: {sale}')
        self.stdout.write(f'  📞 تماس بگیرید: {call_price}')
        self.stdout.write(f'  ⭐ ویژه: {featured}')
        self.stdout.write('=' * 50 + '\n')
