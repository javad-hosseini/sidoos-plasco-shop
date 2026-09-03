import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.products.models import Category

User = get_user_model()


class Command(BaseCommand):
    help = 'ساخت دسته‌بندی‌های تودرتو برای تست'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='پاک کردن دسته‌بندی‌های موجود'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.clear_categories()

        admin = self.get_admin_user()

        self.stdout.write('🏗️  در حال ساخت دسته‌بندی‌های تودرتو...')

        categories = self.create_category_tree(admin)

        self.stdout.write(self.style.SUCCESS(
            f'✅ {len(categories)} دسته‌بندی ساخته شد'
        ))
        self.print_tree()

    def get_admin_user(self):
        """دریافت یا ساخت کاربر ادمین"""
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            self.stdout.write('👤 کاربر ادمین ساخته شد')
        return admin

    def create_category_tree(self, admin):
        """ساخت درخت دسته‌بندی با عمق ۳-۴ سطح"""

        # تعریف ساختار درختی
        tree = {
            'محصولات آشپزخانه': {
                'ابزارآلات آشپزخانه': ['پوست کن', 'چاقو تیزکن', 'جا ادویه', 'نمک پاش'],
                'ظروف نگهداری': ['ظرف دربسته', 'بطری روغن', 'ظرف حبوبات'],
                'ظروف سرو': ['سینی', 'بشقاب', 'کاسه'],
            },
            'محصولات بهداشتی ساختمانی': {
                'لوازم توالت فرنگی': ['فلوتر', 'پمپ تخلیه', 'کیت نصب درب', 'دکمه تخلیه'],
                'سیفون‌ها': [
                    'سیفون فانتزی (غیر هم سطح)',
                    'سیفون فانتزی (هم سطح)',
                    'سیفون کلاسیک ظرفشویی',
                    'سیفون کششی',
                    'سیفون روشویی',
                    'سیفون وان و زیردوشی',
                ],
                'کفشورها': ['کفشور پایه بلند', 'کفشور پلمپ دار', 'کفشور خطی'],
                'سردوش‌ها': ['سردوش کوچک', 'سردوش گرد', 'سردوش مربع', 'سردوش تلفنی'],
                'قطعات و اتصالات': ['زیرآب', 'واشر', 'پیچ یدکی', 'آبریزها'],
            },
            'پیچ و رولپلاک': {
                'پیچ چوب': ['پیچ چهارسو', 'پیچ دوسو', 'پیچ سیدوس (آریا)'],
                'رولپلاک': ['رولپلاک لبه دار', 'رولپلاک شاخک دار', 'رولپلاک خاردار'],
                'پنج بوکسی': ['پنج بوکسی نوک تیز'],
            },
            'گلدان و آبپاش': {
                'گلدان': [
                    'گلدان استوانه‌ای',
                    'گلدان آجری',
                    'گلدان مهرآسا',
                    'گلدان دیواری',
                    'گلدان کاکتوسی',
                    'گلدان نرده‌ای',
                ],
                'زیرگلدانی': ['زیرگلدانی مسی', 'زیرگلدانی مربع'],
                'آبپاش': ['آبپاش طرح گلبرگ', 'محلول پاش'],
            },
        }

        created = []

        for main_name, sub_cats in tree.items():
            # سطح ۱
            main_cat, created_flag = Category.objects.get_or_create(
                name=main_name,
                parent=None,
                creator=admin,
            )
            created.append(main_cat)

            if created_flag:
                self.stdout.write(f'  ✅ {main_name}')

            for sub_name, sub_sub_cats in sub_cats.items():
                # سطح ۲
                sub_cat, _ = Category.objects.get_or_create(
                    name=sub_name,
                    parent=main_cat,
                    creator=admin,
                )
                created.append(sub_cat)

                if isinstance(sub_sub_cats, list):
                    for sub_sub_name in sub_sub_cats:
                        # سطح ۳
                        sub_sub_cat, _ = Category.objects.get_or_create(
                            name=sub_sub_name,
                            parent=sub_cat,
                            creator=admin,
                        )
                        created.append(sub_sub_cat)

                        # سطح ۴ (برای تست عمق بیشتر)
                        if sub_sub_name in ['گلدان استوانه‌ای', 'گلدان آجری', 'سیفون فانتزی (غیر هم سطح)']:
                            for i in range(2):
                                sub_sub_sub, _ = Category.objects.get_or_create(
                                    name=f'{sub_sub_name} - سری {i + 1}',
                                    parent=sub_sub_cat,
                                    creator=admin,
                                )
                                created.append(sub_sub_sub)

        return created

    def clear_categories(self):
        """پاک کردن تمام دسته‌بندی‌ها"""
        self.stdout.write('🗑️  در حال پاک کردن دسته‌بندی‌ها...')
        count = Category.objects.count()
        Category.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'✅ {count} دسته‌بندی پاک شد'))

    def print_tree(self):
        """چاپ درخت دسته‌بندی"""
        self.stdout.write('\n📁 ساختار دسته‌بندی:')
        self.stdout.write('=' * 50)

        main_cats = Category.objects.filter(parent__isnull=True)
        for main in main_cats:
            self.stdout.write(f'├── {main.name}')
            for sub in main.children.all():
                self.stdout.write(f'│   ├── {sub.name}')
                for sub_sub in sub.children.all():
                    self.stdout.write(f'│   │   ├── {sub_sub.name}')
                    for sub_sub_sub in sub_sub.children.all():
                        self.stdout.write(f'│   │   │   └── {sub_sub_sub.name}')

        self.stdout.write('=' * 50 + '\n')