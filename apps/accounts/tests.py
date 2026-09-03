# apps/accounts/tests.py
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.hashers import make_password

User = get_user_model()


class AuthenticationBackendTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            phone_number='+1234567890',
            password=make_password('testpass123'),
            has_price_access=True
        )

    def test_authenticate_with_username(self):
        user = authenticate(username='testuser', password='testpass123')
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'testuser')

    def test_authenticate_with_email(self):
        user = authenticate(username='test@example.com', password='testpass123')
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'test@example.com')

    def test_authenticate_with_phone(self):
        user = authenticate(username='+1234567890', password='testpass123')
        self.assertIsNotNone(user)
        self.assertEqual(user.phone_number, '+1234567890')

    def test_duplicate_email_is_not_ambiguous(self):
        User.objects.create(
            username='otheruser',
            email='test@example.com',
            phone_number='+0987654321',
            password=make_password('testpass123'),
            has_price_access=True,
        )
        user = authenticate(username='test@example.com', password='testpass123')
        self.assertIsNone(user)

    def test_authenticate_with_wrong_password(self):
        user = authenticate(username='testuser', password='wrongpassword')
        self.assertIsNone(user)

    def test_has_price_access_field(self):
        self.assertTrue(self.user.has_price_access)

        user2 = User.objects.create(
            username='testuser2',
            email='test2@example.com',
            phone_number='+0987654321',
            password=make_password('testpass123'),
            has_price_access=False
        )
        self.assertFalse(user2.has_price_access)


class ProfilePageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username='pf-user',
            first_name='رضا',
            phone_number='09120000000',
            password=make_password('testpass123'),
        )

    def _image(self):
        return SimpleUploadedFile(
            name='p.gif',
            content=(
                b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00'
                b'\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00'
                b'\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
            ),
            content_type='image/gif',
        )

    def test_profile_requires_login(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)

    def test_profile_renders_empty_state(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile.html')
        self.assertContains(response, 'محصولات ذخیره‌شده')
        self.assertContains(response, 'رفتن به فروشگاه')

    def test_profile_lists_saved_and_liked_products(self):
        from apps.products.models import Category, Product, ProductLike, ProductSave

        category = Category.objects.create(name='آشپزخانه', creator=self.user)
        product = Product.objects.create(
            name='قابلمه',
            description='x',
            price=300000,
            cover_image=self._image(),
            published=True,
            creator=self.user,
            category=category,
        )
        ProductSave.objects.create(user=self.user, product=product)
        ProductLike.objects.create(user=self.user, product=product)

        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'قابلمه')
        # default has_price_access=True -> price shown
        self.assertContains(response, 'تومان')

    def test_profile_logout_is_post(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)