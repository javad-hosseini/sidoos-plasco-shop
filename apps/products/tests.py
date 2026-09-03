import unittest

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse

from .models import Category, Product, ProductLike, ProductSave


class ProductCategoryTests(TestCase):
    def setUp(self):
        """Set up test data with admin and regular users."""
        # Create a superuser for admin panel access
        self.admin_user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        # Create a regular user for testing permissions
        self.regular_user = get_user_model().objects.create_user(
            username='regular-user',
            password='pass12345'
        )
        # Log in as admin by default
        self.client.force_login(self.admin_user)

    @staticmethod
    def _image_file():
        """Create a test GIF image file."""
        return SimpleUploadedFile(
            name='test.gif',
            content=(
                b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00'
                b'\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00'
                b'\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
            ),
            content_type='image/gif'
        )

    @unittest.skip("Admin panel tests are handled by Django/Jazzmin")
    def test_admin_can_create_subcategory_via_admin_panel(self):
        """Skip: Admin category creation is handled by Django/Jazzmin."""
        pass

    @unittest.skip("Admin panel tests are handled by Django/Jazzmin")
    def test_regular_user_cannot_access_admin_panel(self):
        """Skip: Admin access control is handled by Django/Jazzmin."""
        pass

    @unittest.skip("Admin panel tests are handled by Django/Jazzmin")
    def test_regular_user_cannot_create_category_via_admin(self):
        """Skip: Category creation permissions are handled by Django/Jazzmin."""
        pass

    def test_category_products_includes_nested_subcategories(self):
        """Test that category_products view includes products from nested categories."""
        root = Category.objects.create(name='Kitchen', creator=self.admin_user)
        child = Category.objects.create(name='Storage', parent=root, creator=self.admin_user)
        grandchild = Category.objects.create(name='Containers', parent=child, creator=self.admin_user)

        root_product = Product.objects.create(
            name='Main Kitchen Box',
            description='Root category product',
            price=100,
            cover_image=self._image_file(),
            published=True,
            creator=self.admin_user,
            category=root,
        )
        nested_product = Product.objects.create(
            name='Deep Container',
            description='Nested category product',
            price=120,
            cover_image=self._image_file(),
            published=True,
            creator=self.admin_user,
            category=grandchild,
        )
        Product.objects.create(
            name='Other Product',
            description='Outside of selected category tree',
            price=90,
            cover_image=self._image_file(),
            published=True,
            creator=self.admin_user,
            category=Category.objects.create(name='Other', creator=self.admin_user),
        )

        response = self.client.get(reverse('products:category_products', args=[root.slug]))

        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertIn(root_product, products)
        self.assertIn(nested_product, products)
        self.assertEqual(len(products), 2)

    def test_product_generates_unicode_slug_on_create(self):
        """Test that products generate Unicode slugs automatically."""
        product = Product.objects.create(
            name='گلدان پلاستیکی',
            description='Unicode slug generation test',
            price=100,
            cover_image=self._image_file(),
            published=True,
            creator=self.admin_user,
        )

        self.assertEqual(product.slug, 'گلدان-پلاستیکی')

    def test_product_generates_fallback_unique_slug_when_slugify_empty(self):
        """Test that products get unique fallback slugs when name is empty."""
        first = Product.objects.create(
            name='!!!',
            description='Fallback slug test',
            price=100,
            cover_image=self._image_file(),
            published=True,
            creator=self.admin_user,
        )
        second = Product.objects.create(
            name='@@@',
            description='Fallback slug uniqueness test',
            price=120,
            cover_image=self._image_file(),
            published=True,
            creator=self.admin_user,
        )

        self.assertEqual(first.slug, 'product')
        self.assertEqual(second.slug, 'product-2')

    def test_product_detail_route_accepts_unicode_slug(self):
        """Test that product detail view works with Unicode slugs."""
        product = Product.objects.create(
            name='سطل آشپزخانه',
            description='Unicode route test',
            price=100,
            cover_image=self._image_file(),
            published=True,
            creator=self.admin_user,
        )

        response = self.client.get(reverse('products:product_detail', args=[product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'سطل آشپزخانه')

    def test_product_detail_page_renders_price_and_related(self):
        category = Category.objects.create(name='آشپزخانه', creator=self.admin_user)
        product = Product.objects.create(
            name='قابلمه بزرگ',
            description='<p>توضیح محصول</p>',
            price=250000,
            on_sale_price=200000,
            cover_image=self._image_file(),
            published=True,
            creator=self.admin_user,
            category=category,
        )
        sibling = Product.objects.create(
            name='ماهیتابه',
            description='x',
            price=90000,
            cover_image=self._image_file(),
            published=True,
            creator=self.admin_user,
            category=category,
        )

        response = self.client.get(
            reverse('products:product_detail', args=[product.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/product_detail.html')
        # price visible for an authenticated has_price_access user
        self.assertContains(response, 'تومان')
        self.assertContains(response, 'توضیحات محصول')
        # sibling shows up in the related rail
        self.assertContains(response, sibling.name)
        # save/like controls are wired to the toggle endpoints
        self.assertContains(response, reverse('products:toggle_like', args=[product.id]))

    def test_product_detail_hides_price_for_anonymous(self):
        product = Product.objects.create(
            name='سبد نان',
            description='x',
            price=120000,
            cover_image=self._image_file(),
            published=True,
            creator=self.admin_user,
        )
        response = Client().get(
            reverse('products:product_detail', args=[product.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ورود برای مشاهده قیمت')

    def test_toggle_save_creates_and_deletes_save(self):
        """Test that users can save and unsave products."""
        product = Product.objects.create(
            name='Save Toggle Product',
            description='Save toggle test',
            price=100,
            cover_image=self._image_file(),
            published=True,
            creator=self.admin_user,
        )

        url = reverse('products:toggle_save', args=[product.id])
        create_response = self.client.post(url)
        self.assertEqual(create_response.status_code, 200)
        self.assertJSONEqual(create_response.content, {'saved': True})
        self.assertTrue(ProductSave.objects.filter(user=self.admin_user, product=product).exists())

        delete_response = self.client.post(url)
        self.assertEqual(delete_response.status_code, 200)
        self.assertJSONEqual(delete_response.content, {'saved': False})
        self.assertFalse(ProductSave.objects.filter(user=self.admin_user, product=product).exists())

    def test_toggle_like_creates_and_deletes_like(self):
        """Test that users can like and unlike products."""
        product = Product.objects.create(
            name='Like Toggle Product',
            description='Like toggle test',
            price=100,
            cover_image=self._image_file(),
            published=True,
            creator=self.admin_user,
        )

        url = reverse('products:toggle_like', args=[product.id])
        create_response = self.client.post(url)
        self.assertEqual(create_response.status_code, 200)
        self.assertJSONEqual(create_response.content, {'liked': True})
        self.assertTrue(ProductLike.objects.filter(user=self.admin_user, product=product).exists())

        delete_response = self.client.post(url)
        self.assertEqual(delete_response.status_code, 200)
        self.assertJSONEqual(delete_response.content, {'liked': False})
        self.assertFalse(ProductLike.objects.filter(user=self.admin_user, product=product).exists())

    def test_toggle_endpoints_require_authentication(self):
        """Test that toggle endpoints redirect unauthenticated users."""
        product = Product.objects.create(
            name='Auth Required Product',
            description='Auth test',
            price=100,
            cover_image=self._image_file(),
            published=True,
            creator=self.admin_user,
        )
        anonymous_client = Client()

        save_response = anonymous_client.post(reverse('products:toggle_save', args=[product.id]))
        like_response = anonymous_client.post(reverse('products:toggle_like', args=[product.id]))

        self.assertEqual(save_response.status_code, 302)
        self.assertEqual(like_response.status_code, 302)


class ProductPricingValidationTests(TestCase):
    """Test product pricing validation rules."""

    @staticmethod
    def _image_file():
        """Create a test GIF image file for pricing tests."""
        return SimpleUploadedFile(
            name='pricing-test.gif',
            content=(
                b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00'
                b'\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00'
                b'\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
            ),
            content_type='image/gif',
        )

    def setUp(self):
        """Create a user for product creation."""
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_sale_price_cannot_exceed_base_price(self):
        """Test that sale price cannot be greater than base price."""
        from django.core.exceptions import ValidationError

        product = Product(
            name='Invalid Sale Price',
            description='test',
            price=100,
            on_sale_price=101,
            cover_image=self._image_file(),
            creator=self.user,
        )
        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_call_for_price_cannot_have_sale_price(self):
        """Test that call_for_price products cannot have a sale price."""
        from django.core.exceptions import ValidationError

        product = Product(
            name='Call For Price',
            description='test',
            price=0,
            on_sale_price=50,
            call_for_price=True,
            cover_image=self._image_file(),
            creator=self.user,
        )
        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_call_for_price_normalizes_price_to_zero(self):
        """Test that call_for_price products normalize price to zero."""
        product = Product(
            name='Call For Price Normalized',
            description='test',
            price=500,
            call_for_price=True,
            cover_image=self._image_file(),
            creator=self.user,
        )
        product.full_clean()
        self.assertEqual(product.price, 0)
        self.assertIsNone(product.on_sale_price)

    def test_valid_sale_price_is_accepted(self):
        """Test that a valid sale price is accepted."""
        product = Product(
            name='Valid Sale Price',
            description='test',
            price=100,
            on_sale_price=80,
            cover_image=self._image_file(),
            creator=self.user,
        )
        product.full_clean()
        self.assertEqual(product.price, 100)
        self.assertEqual(product.on_sale_price, 80)

    def test_discount_percentage_calculation(self):
        """Test that discount percentage is calculated correctly."""
        product = Product(
            name='Discount Test',
            description='test',
            price=100,
            on_sale_price=80,
            cover_image=self._image_file(),
            creator=self.user,
        )
        product.full_clean()
        product.save()

        discount = product.get_discount_percentage()
        self.assertEqual(discount, 20.0)

    def test_no_discount_when_no_sale_price(self):
        """Test that no discount is shown when there's no sale price."""
        product = Product(
            name='No Discount',
            description='test',
            price=100,
            on_sale_price=None,
            cover_image=self._image_file(),
            creator=self.user,
        )
        product.full_clean()
        product.save()

        discount = product.get_discount_percentage()
        self.assertIsNone(discount)
