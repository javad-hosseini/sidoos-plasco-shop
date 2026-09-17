from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.core.exceptions import ImproperlyConfigured
import requests

from apps.sms_service.services.provider import (
    BaseSmsProvider,
    MeliPayamakRestProvider,
    ConsoleSmsProvider,
    get_sms_provider,
    ProviderResult,
)


class ProviderLayerTest(TestCase):
    def test_console_provider_succeeds(self):
        provider = ConsoleSmsProvider()
        res = provider.send_simple_sms(["09121112233"], "متن تست کنسول")
        self.assertTrue(res.success)
        self.assertTrue(res.rec_id.startswith("MOCK-"))

    def test_console_provider_empty_recipients_or_text(self):
        # MeliPayamakRestProvider handles empty inputs
        prov = MeliPayamakRestProvider(
            username="u", password="p", from_number="5000", base_url="http://mock.test"
        )
        res_empty_rec = prov.send_simple_sms([], "متن")
        self.assertFalse(res_empty_rec.success)
        self.assertEqual(res_empty_rec.error_code, "EMPTY_RECIPIENTS")

        res_empty_text = prov.send_simple_sms(["09121112233"], "   ")
        self.assertFalse(res_empty_text.success)
        self.assertEqual(res_empty_text.error_code, "EMPTY_TEXT")

    def test_melipayamak_missing_credentials_raises_exception(self):
        with self.assertRaises(ImproperlyConfigured):
            MeliPayamakRestProvider(username="", password="", from_number="")

    @patch("requests.post")
    def test_melipayamak_successful_send(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "2458963214"  # valid recId > 15
        mock_post.return_value = mock_response

        prov = MeliPayamakRestProvider(
            username="test_user",
            password="test_pass",
            from_number="50001234",
            base_url="http://mock.test",
        )
        res = prov.send_simple_sms(["09121112233"], "تست وب‌سرویس")
        self.assertTrue(res.success)
        self.assertEqual(res.rec_id, "2458963214")

    @patch("requests.post")
    def test_melipayamak_error_code_insufficient_credit(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "2"  # Error 2: insufficient credit
        mock_post.return_value = mock_response

        prov = MeliPayamakRestProvider(
            username="test_user",
            password="test_pass",
            from_number="50001234",
            base_url="http://mock.test",
        )
        res = prov.send_simple_sms(["09121112233"], "تست")
        self.assertFalse(res.success)
        self.assertEqual(res.error_code, "2")
        self.assertIn("اعتبار", res.error_message)

    @patch("requests.post")
    def test_melipayamak_timeout_handled_gracefully(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

        prov = MeliPayamakRestProvider(
            username="test_user",
            password="test_pass",
            from_number="50001234",
            base_url="http://mock.test",
        )
        res = prov.send_simple_sms(["09121112233"], "تست")
        self.assertFalse(res.success)
        self.assertEqual(res.error_code, "TIMEOUT")
        self.assertIn("مهلت زمانی", res.error_message)

    @override_settings(SMS_CONSOLE_MODE=True)
    def test_get_sms_provider_returns_console_mode(self):
        prov = get_sms_provider()
        self.assertIsInstance(prov, ConsoleSmsProvider)

