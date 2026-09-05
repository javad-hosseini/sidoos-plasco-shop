import itertools
import random
import re
from datetime import timedelta
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from PIL import Image, ImageDraw, ImageFont

from apps.blogs.models import Article

fake = Faker('fa_IR')

# Blog post titles are built from a prefix x topic grid so they read like
# real headlines instead of generic Faker word-salad.
TITLE_PREFIXES = [
    'راهنمای کامل انتخاب',
    'ده نکته درباره',
    'همه چیز درباره',
    'راهنمای خرید',
    'نکات کاربردی برای نگهداری از',
    'بررسی تخصصی',
    'چگونه بهترین',
    'اشتباهات رایج در خرید',
    'مزایا و معایب',
    'آموزش گام به گام',
]

TITLE_TOPICS = [
    'گلدان‌های آپارتمانی',
    'سیفون آشپزخانه و حمام',
    'کفشور سرویس بهداشتی',
    'رولپلاک و پیچ ساختمانی',
    'ظروف استیل آشپزخانه',
    'پوست کن و ابزار برش',
    'سردوش حمام',
    'ابزارآلات آشپزخانه',
    'محصولات بهداشتی ساختمان',
    'دکوراسیون با گیاهان',
    'نظافت لوازم آشپزخانه',
    'گلدان‌های سرامیکی',
]

CONTENT_HEADINGS = [
    'چرا این موضوع اهمیت دارد',
    'نکات کلیدی',
    'راهنمای خرید',
    'روش نگهداری صحیح',
    'اشتباهات رایج',
    'مزایا و معایب',
    'تجربه کاربران',
    'پرسش‌های متداول',
]

TAGS = [
    'آشپزخانه', 'دکوراسیون', 'گیاهان آپارتمانی', 'بهداشتی ساختمان',
    'نکات خانه‌داری', 'ابزارآلات', 'راهنمای خرید', 'دیزاین داخلی',
    'باغبانی', 'تعمیرات خانگی',
]

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

# Matches Article.clean()'s slug charset (Persian letters, \w, spaces, hyphens)
# so a generated slug never fails full_clean() validation.
SLUG_UNSAFE_CHARS_RE = re.compile(r'[^\w\u0600-\u06FF\s\-]')


class Command(BaseCommand):
    help = 'Generate mock blog articles for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Number of articles to create (default: 50)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete previously generated articles first'
        )

    def handle(self, *args, **options):
        count = options['count']

        if options['clear']:
            self.clear_articles()

        self.stdout.write(f'📝  Generating {count} articles...')

        # Preload existing titles/slugs so new ones never collide with rows
        # already in the database.
        self.used_titles = set(Article.objects.values_list('title', flat=True))
        self.used_slugs = set(Article.objects.values_list('slug', flat=True))
        self.font = self.load_font()

        articles = self.create_articles(count)

        self.print_summary(articles)

    def create_articles(self, count):
        articles = []

        for i, title in enumerate(self.generate_unique_titles(count)):
            is_published, published_at = self.get_publication_state()
            content = self.build_content()
            summary = fake.paragraph(nb_sentences=random.randint(2, 3))

            article = Article(
                title=title,
                slug=self.get_unique_slug(title),
                summary=summary,
                content=content,
                reading_time=random.randint(2, 15),
                is_published=is_published,
                published_at=published_at,
                meta_title=title,
                meta_description=summary,
                og_title=title,
                og_description=summary,
            )

            image_content = self.create_placeholder_image(title)
            article.featured_image.save(
                f'article_{i}_{random.randint(1000, 9999)}.jpg',
                image_content,
                save=False
            )

            article.save()
            article.tags.add(*random.sample(TAGS, k=random.randint(2, 4)))
            articles.append(article)

            if (i + 1) % 10 == 0:
                self.stdout.write(f'  ⏳ {i + 1}/{count} articles created...')

        return articles

    def generate_unique_titles(self, count):
        combos = list(itertools.product(TITLE_PREFIXES, TITLE_TOPICS))
        random.shuffle(combos)

        titles = []
        for prefix, topic in combos:
            if len(titles) >= count:
                return titles
            title = f'{prefix} {topic}'
            if title not in self.used_titles:
                self.used_titles.add(title)
                titles.append(title)

        # Grid exhausted (very large --count) - keep going with a unique
        # numeric suffix so titles never collide.
        while len(titles) < count:
            prefix, topic = random.choice(combos)
            suffix = fake.unique.random_int(min=100, max=99999)
            title = f'{prefix} {topic} (شماره {suffix})'
            if title not in self.used_titles:
                self.used_titles.add(title)
                titles.append(title)

        return titles

    def get_unique_slug(self, title):
        cleaned = SLUG_UNSAFE_CHARS_RE.sub(' ', title)
        base_slug = re.sub(r'\s+', '-', cleaned.strip())

        candidate = base_slug
        suffix = 2
        while candidate in self.used_slugs:
            candidate = f'{base_slug}-{suffix}'
            suffix += 1

        self.used_slugs.add(candidate)
        return candidate

    def build_content(self):
        """Multi-heading HTML body so front-end table-of-contents logic has real headings to parse."""
        headings = random.sample(CONTENT_HEADINGS, k=random.randint(2, 4))

        parts = [f'<p>{fake.paragraph(nb_sentences=random.randint(3, 5))}</p>']

        for heading in headings:
            parts.append(f'<h2>{heading}</h2>')
            for _ in range(random.randint(1, 2)):
                parts.append(f'<p>{fake.paragraph(nb_sentences=random.randint(3, 6))}</p>')

        parts.append('<h2>جمع‌بندی</h2>')
        parts.append(f'<p>{fake.paragraph(nb_sentences=random.randint(2, 4))}</p>')

        return '\n'.join(parts)

    def get_publication_state(self):
        roll = random.random()

        if roll < 0.20:
            return False, None  # draft

        if roll < 0.30:
            # scheduled: published flag on, publish date in the future
            published_at = timezone.now() + timedelta(days=random.randint(1, 30))
            return True, published_at

        # published: publish date sometime in the last ~18 months
        published_at = timezone.now() - timedelta(
            days=random.randint(0, 540),
            hours=random.randint(0, 23),
        )
        return True, published_at

    def load_font(self, size=42):
        """Resolve the Persian font once and reuse it for every placeholder image."""
        for font_path in FONT_CANDIDATES:
            if Path(font_path).exists():
                return ImageFont.truetype(font_path, size)
        return ImageFont.load_default()

    def create_placeholder_image(self, title, width=1200, height=675):
        """Build a simple 16:9 placeholder cover image with Pillow."""
        bg_color = random.choice(PLACEHOLDER_COLORS)

        img = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        margin = 60
        draw.rectangle(
            [margin, margin, width - margin, height - margin],
            outline=(100, 100, 100),
            width=3
        )

        try:
            bbox = draw.textbbox((0, 0), title, font=self.font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            x = (width - text_width) / 2
            y = (height - text_height) / 2

            draw.text((x, y), title, fill=(50, 50, 50), font=self.font)
        except Exception:
            # Font can't render this text (missing glyphs, etc.) - keep the plain rectangle.
            pass

        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)

        return ContentFile(buffer.read())

    def clear_articles(self):
        self.stdout.write('🗑️  Deleting existing articles...')
        count = Article.objects.count()
        Article.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'✅ Deleted {count} articles'))

    def print_summary(self, articles):
        now = timezone.now()
        total = len(articles)
        published = sum(1 for a in articles if a.is_published and a.published_at and a.published_at <= now)
        scheduled = sum(1 for a in articles if a.is_published and a.published_at and a.published_at > now)
        draft = sum(1 for a in articles if not a.is_published)

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('📊 Summary:')
        self.stdout.write(f'  🎯 Total articles: {total}')
        self.stdout.write(f'  ✅ Published: {published}')
        self.stdout.write(f'  ⏰ Scheduled: {scheduled}')
        self.stdout.write(f'  📝 Draft: {draft}')
        self.stdout.write('=' * 50 + '\n')
