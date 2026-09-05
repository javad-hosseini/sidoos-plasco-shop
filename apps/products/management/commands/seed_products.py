import random
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand
from faker import Faker
from PIL import Image
from io import BytesIO
import os

from apps.products.models import Category, Product

User = get_user_model()
fake = Faker('fa_IR')

# ============================================================================
# CONFIGURATION
# ============================================================================

# Expected image directory:
#
#   <PROJECT_ROOT>/media/products/SampleCovers/
#
# This uses Django's MEDIA_ROOT instead of calculating the project root
# manually, which makes it much more reliable.
SAMPLE_COVERS_DIR = (
        Path(settings.MEDIA_ROOT)
        / 'products'
        / 'SampleCovers'
)

SUPPORTED_IMAGE_EXTENSIONS = {
    '.jpg',
    '.jpeg',
    '.png',
    '.webp',
    '.gif',
    '.bmp',
}

# Image processing settings
COVER_IMAGE_SIZE = (800, 800)  # 1:1 aspect ratio
IMAGE_QUALITY = 85  # JPEG quality (1-100)

# ============================================================================
# PRODUCT DATA
# ============================================================================

PRODUCT_NAME_MAP = {
    'پوست کن': [
        'پوست کن تیغه آلمانی',
        'پوست کن طرح ترک',
        'پوست کن معمولی',
    ],

    'چاقو تیزکن': [
        'چاقو تیزکن جدید',
        'چاقو تیزکن حرفه‌ای',
    ],

    'جا ادویه': [
        'جا ادویه سه حالته',
        'جا ادویه گردان',
    ],

    'گلدان': [
        'گلدان استوانه‌ای',
        'گلدان آجری',
        'گلدان کاکتوسی',
    ],

    'سردوش': [
        'سردوش گرد',
        'سردوش مربعی',
        'سردوش تلفنی',
    ],

    'سیفون': [
        'سیفون فانتزی',
        'سیفون کلاسیک',
        'سیفون کششی',
    ],

    'پیچ': [
        'پیچ چهارسو',
        'پیچ دوسو',
        'پیچ آلن',
    ],

    'رولپلاک': [
        'رولپلاک لبه دار',
        'رولپلاک شاخک دار',
    ],
}

MATERIALS = [
    'پلاستیک فشرده',
    'استیل ضد زنگ',
    'آلومینیوم',
    'پلی‌اتیلن',
    'ABS',
]

FEATURES = [
    'کیفیت بالا',
    'طراحی ارگونومیک',
    'دوام طولانی',
    'نصب آسان',
    'مناسب مصارف خانگی',
    'بسته‌بندی استاندارد',
]

EXTRA_TAGS = [
    'کیفیت بالا',
    'ارسال سریع',
    'عمده فروشی',
    'ضمانت',
    'جدید',
]


# ============================================================================
# COMMAND
# ============================================================================

class Command(BaseCommand):
    help = (
        'Generate mock products using existing categories '
        'and local sample images'
    )

    # ------------------------------------------------------------------------
    # Arguments
    # ------------------------------------------------------------------------

    def add_arguments(self, parser):

        parser.add_argument(
            '--count',
            type=int,
            default=200,
            help='Number of products to create (default: 200)',
        )

        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete previously generated products first',
        )

        parser.add_argument(
            '--category',
            type=str,
            help='Only create products under this main category name',
        )

    # ------------------------------------------------------------------------
    # Main handler
    # ------------------------------------------------------------------------

    def handle(self, *args, **options):

        count = options['count']

        # ====================================================================
        # Validate count
        # ====================================================================

        if count < 1:
            self.stdout.write(
                self.style.ERROR(
                    '❌ Product count must be greater than 0.'
                )
            )

            return

        # ====================================================================
        # Clear existing products
        # ====================================================================

        if options['clear']:
            self.clear_products()

        # ====================================================================
        # Check categories
        # ====================================================================

        if not Category.objects.exists():
            self.stdout.write(
                self.style.ERROR(
                    '❌ No categories found!'
                )
            )

            self.stdout.write(
                'Run this first:'
            )

            self.stdout.write(
                '  python manage.py seed_categories'
            )

            return

        # ====================================================================
        # Get main categories
        # ====================================================================

        main_categories = Category.objects.filter(
            parent__isnull=True
        )

        if options['category']:

            main_categories = main_categories.filter(
                name__icontains=options['category']
            )

            if not main_categories.exists():
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ Category "{options["category"]}" not found'
                    )
                )

                return

        main_categories = list(main_categories)

        # ====================================================================
        # Load sample images
        # ====================================================================

        self.stdout.write('')
        self.stdout.write(
            '🔎 Loading sample product images...'
        )

        self.sample_covers = self.load_sample_covers()

        # Extra confirmation after loading.
        self.stdout.write(
            f'🔢 Final sample cover count: '
            f'{len(self.sample_covers)}'
        )

        if not self.sample_covers:
            self.stdout.write('')
            self.stdout.write(
                self.style.ERROR(
                    '❌ Cannot generate products because no sample '
                    'images were found.'
                )
            )

            return

        # Start with a randomized order.
        self.shuffle_sample_covers()

        # ====================================================================
        # Image count warning
        # ====================================================================

        if len(self.sample_covers) < count:

            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Only {len(self.sample_covers)} unique images '
                    f'available for {count} products.'
                )
            )

            self.stdout.write(
                '   Images will be reused only after the entire '
                'image pool has been exhausted.'
            )

        else:

            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Enough images available for all {count} '
                    f'products without reuse.'
                )
            )

        # ====================================================================
        # Prepare names
        # ====================================================================

        self.used_names = set(
            Product.objects.values_list(
                'name',
                flat=True,
            )
        )

        self.stdout.write(
            f'📝 Existing product names loaded: '
            f'{len(self.used_names)}'
        )

        # ====================================================================
        # Generate products
        # ====================================================================

        self.stdout.write('')
        self.stdout.write(
            f'🏭 Generating {count} products...'
        )
        self.stdout.write('')

        products = self.create_products(
            count,
            main_categories,
        )

        # ====================================================================
        # Summary
        # ====================================================================

        self.print_summary(products)

    # =========================================================================
    # IMAGE HANDLING
    # =========================================================================

    def process_image_to_square(self, image_path, output_path=None):
        """
        Process an image to be a 1:1 square ratio.

        This function:
        1. Opens the image
        2. Crops it to a square (center crop)
        3. Resizes it to COVER_IMAGE_SIZE (800x800 by default)
        4. Saves it with optimization

        Returns the processed image file path or None if processing fails.
        """
        try:
            # Open the image
            img = Image.open(image_path)

            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create a white background
                background = Image.new('RGB', img.size, (255, 255, 255))

                if img.mode == 'P':
                    img = img.convert('RGBA')

                # Paste the image on the background
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Get original dimensions
            width, height = img.size

            # Calculate crop dimensions for center square crop
            if width > height:
                # Landscape image - crop width
                left = (width - height) // 2
                top = 0
                right = left + height
                bottom = height
            else:
                # Portrait image - crop height
                left = 0
                top = (height - width) // 2
                right = width
                bottom = top + width

            # Crop to square
            img_cropped = img.crop((left, top, right, bottom))

            # Resize to target size
            img_resized = img_cropped.resize(
                COVER_IMAGE_SIZE,
                Image.Resampling.LANCZOS
            )

            # Save to BytesIO
            img_io = BytesIO()

            # Determine format based on original extension
            ext = image_path.suffix.lower()

            if ext in ['.jpg', '.jpeg']:
                img_resized.save(img_io, format='JPEG', quality=IMAGE_QUALITY, optimize=True)
            elif ext == '.png':
                img_resized.save(img_io, format='PNG', optimize=True)
            elif ext == '.webp':
                img_resized.save(img_io, format='WEBP', quality=IMAGE_QUALITY)
            else:
                # Default to JPEG for other formats
                img_resized.save(img_io, format='JPEG', quality=IMAGE_QUALITY, optimize=True)

            img_io.seek(0)

            return img_io

        except Exception as exc:
            self.stdout.write(
                self.style.WARNING(
                    f'   ⚠️  Image processing failed for {image_path.name}: {exc}'
                )
            )
            return None

    def load_sample_covers(self):
        """
        Find all supported images in:

            MEDIA_ROOT/products/SampleCovers/

        This function intentionally prints a lot of information so that
        path/file problems are immediately visible from the terminal.
        """

        self.stdout.write('')
        self.stdout.write('=' * 75)
        self.stdout.write(
            '🖼️  SAMPLE IMAGE DEBUG INFORMATION'
        )
        self.stdout.write('=' * 75)

        # ---------------------------------------------------------------------
        # Django MEDIA_ROOT
        # ---------------------------------------------------------------------

        media_root = Path(settings.MEDIA_ROOT)

        self.stdout.write('')
        self.stdout.write(
            '📌 Django MEDIA_ROOT configuration:'
        )

        self.stdout.write(
            f'   Raw value: {settings.MEDIA_ROOT!r}'
        )

        self.stdout.write(
            f'   Resolved:  {media_root.resolve()}'
        )

        self.stdout.write(
            f'   Exists:    {media_root.exists()}'
        )

        self.stdout.write(
            f'   Directory: {media_root.is_dir()}'
        )

        # ---------------------------------------------------------------------
        # Expected SampleCovers directory
        # ---------------------------------------------------------------------

        sample_dir = (
                media_root
                / 'products'
                / 'SampleCovers'
        )

        self.stdout.write('')
        self.stdout.write(
            '📂 SampleCovers directory:'
        )

        self.stdout.write(
            f'   Path:     {sample_dir}'
        )

        self.stdout.write(
            f'   Resolved: {sample_dir.resolve()}'
        )

        self.stdout.write(
            f'   Exists:   {sample_dir.exists()}'
        )

        self.stdout.write(
            f'   Is dir:   {sample_dir.is_dir()}'
        )

        # ---------------------------------------------------------------------
        # Directory does not exist
        # ---------------------------------------------------------------------

        if not sample_dir.exists():

            self.stdout.write('')
            self.stdout.write(
                self.style.ERROR(
                    '❌ SampleCovers directory DOES NOT EXIST.'
                )
            )

            self.stdout.write('')
            self.stdout.write(
                '🔍 Checking parent directories:'
            )

            current = sample_dir

            while True:

                self.stdout.write(
                    f'   {current}'
                    f' | exists={current.exists()}'
                    f' | directory={current.is_dir()}'
                )

                if current.parent == current:
                    break

                current = current.parent

            self.stdout.write('')
            self.stdout.write(
                '💡 Django is looking for images here:'
            )

            self.stdout.write(
                f'   {sample_dir.resolve()}'
            )

            self.stdout.write('=' * 75)
            self.stdout.write('')

            return []

        # ---------------------------------------------------------------------
        # Path exists but is not a directory
        # ---------------------------------------------------------------------

        if not sample_dir.is_dir():
            self.stdout.write('')
            self.stdout.write(
                self.style.ERROR(
                    '❌ SampleCovers exists but is NOT a directory.'
                )
            )

            self.stdout.write('=' * 75)
            self.stdout.write('')

            return []

        # ---------------------------------------------------------------------
        # Read directory
        # ---------------------------------------------------------------------

        self.stdout.write('')
        self.stdout.write(
            '📋 Reading SampleCovers contents...'
        )

        try:

            contents = list(
                sample_dir.iterdir()
            )

        except Exception as exc:

            self.stdout.write(
                self.style.ERROR(
                    f'❌ Failed to read directory: {exc}'
                )
            )

            self.stdout.write('=' * 75)
            self.stdout.write('')

            return []

        # ---------------------------------------------------------------------
        # Empty directory
        # ---------------------------------------------------------------------

        if not contents:
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  SampleCovers directory is EMPTY.'
                )
            )

            self.stdout.write('=' * 75)
            self.stdout.write('')

            return []

        # ---------------------------------------------------------------------
        # Print every filesystem entry
        # ---------------------------------------------------------------------

        self.stdout.write(
            f'   Found {len(contents)} filesystem entries.'
        )

        self.stdout.write('')

        for path in sorted(contents):
            self.stdout.write(
                f'   📄 {path.name}'
                f' | file={path.is_file()}'
                f' | directory={path.is_dir()}'
                f' | extension={path.suffix!r}'
            )

        # ---------------------------------------------------------------------
        # Filter supported images
        # ---------------------------------------------------------------------

        self.stdout.write('')
        self.stdout.write(
            '🔎 Filtering supported image files...'
        )

        self.stdout.write(
            '   Supported extensions: '
            + ', '.join(
                sorted(SUPPORTED_IMAGE_EXTENSIONS)
            )
        )

        images = []

        for path in contents:

            # ---------------------------------------------------------------
            # Ignore directories
            # ---------------------------------------------------------------

            if not path.is_file():
                self.stdout.write(
                    f'   ⏭️  SKIP: {path.name}'
                    ' (not a regular file)'
                )

                continue

            # ---------------------------------------------------------------
            # Check extension
            # ---------------------------------------------------------------

            extension = path.suffix.lower()

            if extension not in SUPPORTED_IMAGE_EXTENSIONS:
                self.stdout.write(
                    f'   ⏭️  SKIP: {path.name}'
                    f' (unsupported extension: {extension!r})'
                )

                continue

            # ---------------------------------------------------------------
            # Accept image
            # ---------------------------------------------------------------

            self.stdout.write(
                self.style.SUCCESS(
                    f'   ✅ ACCEPT: {path.name}'
                    f' | extension={extension}'
                    f' | size={path.stat().st_size:,} bytes'
                )
            )

            images.append(path)

        # ---------------------------------------------------------------------
        # Final image result
        # ---------------------------------------------------------------------

        self.stdout.write('')
        self.stdout.write(
            f'📊 Accepted images: '
            f'{len(images)} / {len(contents)}'
        )

        if images:

            self.stdout.write(
                self.style.SUCCESS(
                    '✅ Sample images successfully loaded.'
                )
            )

        else:

            self.stdout.write(
                self.style.ERROR(
                    '❌ No supported images were found.'
                )
            )

        self.stdout.write('=' * 75)
        self.stdout.write('')

        return images

    # ------------------------------------------------------------------------
    # Shuffle image pool
    # ------------------------------------------------------------------------

    def shuffle_sample_covers(self):
        """
        Shuffle the image pool and reset its position.

        Every image is therefore used exactly once before the pool is
        reshuffled and images start being reused.
        """

        random.shuffle(
            self.sample_covers
        )

        self.sample_cover_index = 0

        self.stdout.write(
            f'🔀 Image pool shuffled '
            f'({len(self.sample_covers)} images)'
        )

    # ------------------------------------------------------------------------
    # Get next image
    # ------------------------------------------------------------------------

    def get_next_sample_cover(self):
        """
        Return the next image from the shuffled pool.

        No image is repeated until every available image has been used.
        """

        if not self.sample_covers:
            return None

        # ---------------------------------------------------------------
        # Pool exhausted
        # ---------------------------------------------------------------

        if (
                self.sample_cover_index
                >= len(self.sample_covers)
        ):
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING(
                    '🔄 All sample images have been used. '
                    'Reshuffling image pool...'
                )
            )

            self.shuffle_sample_covers()

        # ---------------------------------------------------------------
        # Select image
        # ---------------------------------------------------------------

        image_path = self.sample_covers[
            self.sample_cover_index
        ]

        self.sample_cover_index += 1

        return image_path

    # =========================================================================
    # ADMIN USER
    # =========================================================================

    def get_admin_user(self):

        admin = User.objects.filter(
            is_superuser=True
        ).first()

        if not admin:
            self.stdout.write(
                '👤 No superuser found. Creating development admin...'
            )

            admin = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123',
            )

            self.stdout.write(
                self.style.SUCCESS(
                    '✅ Development admin created.'
                )
            )

        return admin

    # =========================================================================
    # CATEGORY WEIGHTS
    # =========================================================================

    def get_category_weights(self, main_categories):
        """
        Weight 'گلدان' at 35%.
        The remaining 65% is distributed evenly among other categories.
        """

        others = [
            category
            for category in main_categories
            if 'گلدان' not in category.name
        ]

        other_weight = (
            65 / len(others)
            if others
            else 0
        )

        return [
            35 if 'گلدان' in category.name
            else other_weight
            for category in main_categories
        ]

    # =========================================================================
    # PRODUCT CREATION
    # =========================================================================

    def create_products(
            self,
            count,
            main_categories,
    ):

        admin = self.get_admin_user()

        weights = self.get_category_weights(
            main_categories
        )

        products = []

        for i in range(count):

            # -----------------------------------------------------------------
            # Choose main category
            # -----------------------------------------------------------------

            main_cat = random.choices(
                main_categories,
                weights=weights,
                k=1,
            )[0]

            # -----------------------------------------------------------------
            # Choose nested category
            # -----------------------------------------------------------------

            category = self.get_random_category(
                main_cat
            )

            # -----------------------------------------------------------------
            # Generate unique name
            # -----------------------------------------------------------------

            name = self.get_unique_product_name(
                category
            )

            # -----------------------------------------------------------------
            # Generate pricing
            # -----------------------------------------------------------------

            (
                price,
                on_sale_price,
                call_for_price,
            ) = self.get_pricing()

            # -----------------------------------------------------------------
            # Create Product instance
            # -----------------------------------------------------------------

            product = Product(
                name=name,

                description=self.get_realistic_description(
                    name,
                    category,
                ),

                price=price,

                on_sale_price=on_sale_price,

                call_for_price=call_for_price,

                published=(
                        random.random() < 0.9
                ),

                featured_in_special_sales=(
                        random.random() < 0.25
                ),

                is_featured=(
                        random.random() < 0.15
                ),

                featured_order=(
                    random.randint(1, 100)
                    if random.random() < 0.15
                    else 0
                ),

                creator=admin,

                category=category,
            )

            # -----------------------------------------------------------------
            # Select sample image
            # -----------------------------------------------------------------

            image_path = (
                self.get_next_sample_cover()
            )

            if image_path:

                self.stdout.write(
                    f'   🖼️  Product {i + 1}/{count}'
                    f' → {image_path.name}'
                )

                # -------------------------------------------------------------
                # Process image to 1:1 square format
                # -------------------------------------------------------------

                processed_image = self.process_image_to_square(
                    image_path
                )

                if processed_image:

                    # ---------------------------------------------------------
                    # Generate unique destination filename.
                    #
                    # This keeps Django's media storage from having to deal with
                    # products sharing exactly the same filename.
                    # ---------------------------------------------------------

                    # Use .jpg extension for processed images
                    image_filename = (
                        f'product_{i + 1}_'
                        f'{random.randint(100000, 999999)}'
                        f'.jpg'
                    )

                    try:

                        product.cover_image.save(
                            image_filename,
                            File(processed_image),
                            save=False,
                        )

                        self.stdout.write(
                            f'   ✅ Image processed: '
                            f'{COVER_IMAGE_SIZE[0]}x{COVER_IMAGE_SIZE[1]}px'
                        )

                    except Exception as exc:

                        self.stdout.write(
                            self.style.ERROR(
                                f'   ❌ Failed to attach image '
                                f'{image_path.name}: {exc}'
                            )
                        )

                        raise

                else:

                    self.stdout.write(
                        self.style.WARNING(
                            f'   ⚠️  Image processing failed, '
                            f'attempting to use original...'
                        )
                    )

                    # Fallback to original image
                    image_filename = (
                        f'product_{i + 1}_'
                        f'{random.randint(100000, 999999)}'
                        f'{image_path.suffix.lower()}'
                    )

                    try:

                        with image_path.open(
                                'rb'
                        ) as image_file:

                            product.cover_image.save(
                                image_filename,
                                File(image_file),
                                save=False,
                            )

                    except Exception as exc:

                        self.stdout.write(
                            self.style.ERROR(
                                f'   ❌ Failed to attach image '
                                f'{image_path.name}: {exc}'
                            )
                        )

                        raise

            else:

                self.stdout.write(
                    self.style.WARNING(
                        f'   ⚠️  Product {i + 1}/{count}'
                        ' has no image.'
                    )
                )

            # -----------------------------------------------------------------
            # Save product
            # -----------------------------------------------------------------

            try:

                product.save()

            except Exception as exc:

                self.stdout.write(
                    self.style.ERROR(
                        f'   ❌ Failed to save product '
                        f'"{name}": {exc}'
                    )
                )

                raise

            # -----------------------------------------------------------------
            # Add tags
            # -----------------------------------------------------------------

            try:

                product.tags.add(
                    *self.get_tags(category)
                )

            except Exception as exc:

                self.stdout.write(
                    self.style.WARNING(
                        f'   ⚠️  Failed to add tags to '
                        f'"{name}": {exc}'
                    )
                )

            products.append(product)

            # -----------------------------------------------------------------
            # Progress message
            # -----------------------------------------------------------------

            if (i + 1) % 25 == 0:
                self.stdout.write(
                    f'  ⏳ {i + 1}/{count} products created...'
                )

        return products

    # =========================================================================
    # CATEGORY SELECTION
    # =========================================================================

    def get_random_category(self, main_cat):
        """
        Pick a category at a random depth.

        Distribution:

            depth 1 -> 40%
            depth 2 -> 35%
            depth 3 -> 20%
            depth 4 -> 5%

        If a category has no children at the requested depth,
        the deepest available category is returned.
        """

        depth = random.choices(
            [1, 2, 3, 4],
            weights=[40, 35, 20, 5],
            k=1,
        )[0]

        current = main_cat

        for _ in range(depth - 1):

            children = list(
                current.children.all()
            )

            if not children:
                break

            current = random.choice(
                children
            )

        return current

    # =========================================================================
    # PRODUCT NAMES
    # =========================================================================

    def get_base_product_name(self, category):
        """
        Pick a realistic base name based on the category.
        """

        for key, names in PRODUCT_NAME_MAP.items():

            if (
                    key in category.name
                    or category.name in key
            ):
                return random.choice(
                    names
                )

        return category.name

    # ------------------------------------------------------------------------

    def get_unique_product_name(self, category):
        """
        Generate a product name guaranteed not to collide with an existing
        product or another product generated during this run.
        """

        base = self.get_base_product_name(
            category
        )

        while True:

            suffix = fake.unique.random_int(
                min=1000,
                max=99999,
            )

            candidate = (
                f'{base} مدل {suffix}'
            )

            if candidate not in self.used_names:
                self.used_names.add(
                    candidate
                )

                return candidate

    # =========================================================================
    # PRICING
    # =========================================================================

    def get_pricing(self):
        """
        Generate randomized pricing.

        15% -> Call for price
        30% -> Sale
        55% -> Normal
        """

        # ---------------------------------------------------------------------
        # Call for price
        # ---------------------------------------------------------------------

        if random.random() < 0.15:
            return (
                0,
                None,
                True,
            )

        # ---------------------------------------------------------------------
        # Normal price
        # ---------------------------------------------------------------------

        price = random.randint(
            50000,
            5000000,
        )

        # ---------------------------------------------------------------------
        # Sale price
        # ---------------------------------------------------------------------

        if random.random() < 0.30:
            on_sale = int(
                price
                * random.uniform(
                    0.7,
                    0.9,
                )
            )

            return (
                price,
                on_sale,
                False,
            )

        return (
            price,
            None,
            False,
        )

    # =========================================================================
    # DESCRIPTION
    # =========================================================================

    def get_realistic_description(
            self,
            name,
            category,
    ):

        feature_1 = random.choice(
            FEATURES
        )

        feature_2 = random.choice(
            FEATURES
        )

        material = random.choice(
            MATERIALS
        )

        return (
            f'{name} از جنس {material}. '
            f'دارای {feature_1} و {feature_2}. '
            f'مناسب {category.name}.'
        )

    # =========================================================================
    # TAGS
    # =========================================================================

    def get_tags(self, category):

        tags = [
            category.name
        ]

        parent = category.parent

        while parent:
            tags.append(
                parent.name
            )

            parent = parent.parent

        tags.extend(
            random.sample(
                EXTRA_TAGS,
                k=2,
            )
        )

        return tags

    # =========================================================================
    # CLEAR PRODUCTS
    # =========================================================================

    def clear_products(self):

        self.stdout.write(
            '🗑️  Deleting existing products...'
        )

        count = Product.objects.count()

        Product.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Deleted {count} products'
            )
        )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    def print_summary(self, products):

        total = len(products)

        published = sum(
            1
            for product in products
            if product.published
        )

        sale = sum(
            1
            for product in products
            if product.on_sale_price
        )

        call_price = sum(
            1
            for product in products
            if product.call_for_price
        )

        featured = sum(
            1
            for product in products
            if product.featured_in_special_sales
        )

        self.stdout.write('')
        self.stdout.write('=' * 75)

        self.stdout.write(
            '📊 PRODUCT GENERATION SUMMARY'
        )

        self.stdout.write('=' * 75)

        self.stdout.write(
            f'  🎯 Total products:          {total}'
        )

        self.stdout.write(
            f'  ✅ Published:               {published}'
        )

        self.stdout.write(
            f'  💰 On sale:                 {sale}'
        )

        self.stdout.write(
            f'  📞 Call for price:          {call_price}'
        )

        self.stdout.write(
            f'  ⭐ Featured:                {featured}'
        )

        self.stdout.write(
            f'  🖼️  Sample images available: '
            f'{len(self.sample_covers)}'
        )

        self.stdout.write(
            f'  📐 Image size:              '
            f'{COVER_IMAGE_SIZE[0]}x{COVER_IMAGE_SIZE[1]}px (1:1)'
        )

        self.stdout.write(
            '=' * 75
        )

        self.stdout.write('')