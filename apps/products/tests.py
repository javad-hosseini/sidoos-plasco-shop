from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Category, Product


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
