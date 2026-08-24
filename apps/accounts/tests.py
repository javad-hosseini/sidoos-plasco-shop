# apps/accounts/tests.py
from django.test import TestCase
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