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

    def test_authenticate_with_no_matching_user(self):
        user = authenticate(username='nobody-with-this-name', password='whatever')
        self.assertIsNone(user)

    def test_inactive_user_cannot_authenticate(self):
        self.user.is_active = False
        self.user.save()
        user = authenticate(username='testuser', password='testpass123')
        self.assertIsNone(user)

    def test_phone_number_uniqueness_enforced(self):
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create(
                    username='another-user',
                    phone_number='+1234567890',  # already used by self.user
                    password=make_password('testpass123'),
                )


class LoginViewTests(TestCase):
    """HTTP-level tests for the built-in LoginView, wired to our custom backend."""

    def setUp(self):
        self.user = User.objects.create(
            username='login-user',
            email='login@example.com',
            phone_number='+1112223333',
            password=make_password('correct-password'),
        )

    def test_get_renders_login_form(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')

    def test_successful_login_with_username_redirects(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'login-user',
            'password': 'correct-password',
        })
        self.assertEqual(response.status_code, 302)
        # confirm the session actually holds an authenticated user now
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_successful_login_with_email_redirects(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'login@example.com',
            'password': 'correct-password',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)

    def test_invalid_credentials_shows_form_error(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'login-user',
            'password': 'wrong-password',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertFalse(response.context['form'].is_valid())
        self.assertTrue(response.context['form'].errors)

    def test_already_authenticated_user_redirected_away_from_login(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:login'))
        # redirect_authenticated_user=True on the LoginView
        self.assertEqual(response.status_code, 302)


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

    def test_profile_hides_price_when_access_disabled(self):
        from apps.products.models import Product, ProductSave

        self.user.has_price_access = False
        self.user.save()
        product = Product.objects.create(
            name='دیس بزرگ',
            description='x',
            price=150000,
            cover_image=self._image(),
            published=True,
            creator=self.user,
        )
        ProductSave.objects.create(user=self.user, product=product)

        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'دیس بزرگ')
        self.assertNotContains(response, 'تومان')

    def test_profile_excludes_unpublished_products(self):
        from apps.products.models import Product, ProductSave

        hidden_product = Product.objects.create(
            name='محصول پیش‌نویس',
            description='x',
            price=100000,
            cover_image=self._image(),
            published=False,
            creator=self.user,
        )
        ProductSave.objects.create(user=self.user, product=hidden_product)

        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'محصول پیش‌نویس')