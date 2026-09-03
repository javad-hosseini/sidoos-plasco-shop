from unittest import TestCase


class ProductPricingValidationTests(TestCase):
    @staticmethod
    def _image_file():
        return SimpleUploadedFile(
            name='pricing-test.gif',
            content=(
                b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00'
                b'\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00'
                b'\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
            ),
            content_type='image/gif',
        )

    def test_sale_price_cannot_exceed_base_price(self):
        from django.core.exceptions import ValidationError

        product = Product(
            name='Invalid Sale Price',
            description='test',
            price=100,
            on_sale_price=101,
            cover_image=self._image_file(),
        )
        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_call_for_price_cannot_have_sale_price(self):
        from django.core.exceptions import ValidationError

        product = Product(
            name='Call For Price',
            description='test',
            price=0,
            on_sale_price=50,
            call_for_price=True,
            cover_image=self._image_file(),
        )
        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_call_for_price_normalizes_price_to_zero(self):
        product = Product(
            name='Call For Price Normalized',
            description='test',
            price=500,
            call_for_price=True,
            cover_image=self._image_file(),
        )
        product.full_clean()
        self.assertEqual(product.price, 0)
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse

from .models import Category, Product, ProductLike, ProductSave


class ProductCategoryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='category-user',
            password='pass12345'
        )
        self.client.force_login(self.user)

    @staticmethod
    def _image_file():
        return SimpleUploadedFile(
            name='test.gif',
            content=(
                b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00'
                b'\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00'
                b'\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
            ),
            content_type='image/gif'
        )

    def test_authenticated_user_can_create_subcategory(self):
        parent = Category.objects.create(name='Pots', creator=self.user)

        response = self.client.post(
            reverse('products:category_create'),
            {
                'name': 'Garden Pots',
                'parent': parent.id,
            }
        )

        self.assertRedirects(response, reverse('products:category_list'))
        created = Category.objects.get(name='Garden Pots')
        self.assertEqual(created.parent, parent)
        self.assertEqual(created.creator, self.user)

    def test_category_products_includes_nested_subcategories(self):
        root = Category.objects.create(name='Kitchen', creator=self.user)
        child = Category.objects.create(name='Storage', parent=root, creator=self.user)
        grandchild = Category.objects.create(name='Containers', parent=child, creator=self.user)

        root_product = Product.objects.create(
            name='Main Kitchen Box',
            description='Root category product',
            price=100,
            cover_image=self._image_file(),
            published=True,
            creator=self.user,
            category=root,
        )
        nested_product = Product.objects.create(
            name='Deep Container',
            description='Nested category product',
            price=120,
            cover_image=self._image_file(),
            published=True,
            creator=self.user,
            category=grandchild,
        )
        Product.objects.create(
            name='Other Product',
            description='Outside of selected category tree',
            price=90,
            cover_image=self._image_file(),
            published=True,
            creator=self.user,
            category=Category.objects.create(name='Other', creator=self.user),
        )

        response = self.client.get(reverse('products:category_products', args=[root.slug]))

        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertIn(root_product, products)
        self.assertIn(nested_product, products)
        self.assertEqual(len(products), 2)

    def test_product_generates_unicode_slug_on_create(self):
        product = Product.objects.create(
            name='گلدان پلاستیکی',
            description='Unicode slug generation test',
            price=100,
            cover_image=self._image_file(),
            published=True,
            creator=self.user,
        )

        self.assertEqual(product.slug, 'گلدان-پلاستیکی')

    def test_product_generates_fallback_unique_slug_when_slugify_empty(self):
        first = Product.objects.create(
            name='!!!',
            description='Fallback slug test',
            price=100,
            cover_image=self._image_file(),
            published=True,
            creator=self.user,
        )
        second = Product.objects.create(
            name='@@@',
            description='Fallback slug uniqueness test',
            price=120,
            cover_image=self._image_file(),
            published=True,
            creator=self.user,
        )

        self.assertEqual(first.slug, 'product')
        self.assertEqual(second.slug, 'product-2')

    def test_product_detail_route_accepts_unicode_slug(self):
        product = Product.objects.create(
            name='سطل آشپزخانه',
            description='Unicode route test',
            price=100,
            cover_image=self._image_file(),
            published=True,
            creator=self.user,
        )

        response = self.client.get(reverse('products:product_detail', args=[product.slug]))
        self.assertEqual(response.status_code, 200)

    def test_toggle_save_creates_and_deletes_save(self):
        product = Product.objects.create(
            name='Save Toggle Product',
            description='Save toggle test',
            price=100,
            cover_image=self._image_file(),
            published=True,
            creator=self.user,
        )

        url = reverse('products:toggle_save', args=[product.id])
        create_response = self.client.post(url)
        self.assertEqual(create_response.status_code, 200)
        self.assertJSONEqual(create_response.content, {'saved': True})
        self.assertTrue(ProductSave.objects.filter(user=self.user, product=product).exists())

        delete_response = self.client.post(url)
        self.assertEqual(delete_response.status_code, 200)
        self.assertJSONEqual(delete_response.content, {'saved': False})
        self.assertFalse(ProductSave.objects.filter(user=self.user, product=product).exists())

    def test_toggle_like_creates_and_deletes_like(self):
        product = Product.objects.create(
            name='Like Toggle Product',
            description='Like toggle test',
            price=100,
            cover_image=self._image_file(),
            published=True,
            creator=self.user,
        )

        url = reverse('products:toggle_like', args=[product.id])
        create_response = self.client.post(url)
        self.assertEqual(create_response.status_code, 200)
        self.assertJSONEqual(create_response.content, {'liked': True})
        self.assertTrue(ProductLike.objects.filter(user=self.user, product=product).exists())

        delete_response = self.client.post(url)
        self.assertEqual(delete_response.status_code, 200)
        self.assertJSONEqual(delete_response.content, {'liked': False})
        self.assertFalse(ProductLike.objects.filter(user=self.user, product=product).exists())

    def test_toggle_endpoints_require_authentication(self):
        product = Product.objects.create(
            name='Auth Required Product',
            description='Auth test',
            price=100,
            cover_image=self._image_file(),
            published=True,
            creator=self.user,
        )
        anonymous_client = Client()

        save_response = anonymous_client.post(reverse('products:toggle_save', args=[product.id]))
        like_response = anonymous_client.post(reverse('products:toggle_like', args=[product.id]))

        self.assertEqual(save_response.status_code, 302)
        self.assertEqual(like_response.status_code, 302)
