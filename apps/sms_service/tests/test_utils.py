from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.sms_service.utils import (
    normalize_phone_number,
    is_valid_iranian_mobile,
    validate_iranian_mobile,
    format_personalized_message,
    calculate_sms_parts,
)

User = get_user_model()


class PhoneNumberUtilsTest(TestCase):
    def test_normalize_standard_09_format(self):
        self.assertEqual(normalize_phone_number("09123456789"), "09123456789")

    def test_normalize_persian_and_arabic_digits(self):
        self.assertEqual(normalize_phone_number("۰۹۱۲۳۴۵۶۷۸۹"), "09123456789")
        self.assertEqual(normalize_phone_number("٠٩١٢٣٤٥٦٧٨٩"), "09123456789")

    def test_normalize_with_plus_98_prefix(self):
        self.assertEqual(normalize_phone_number("+989123456789"), "09123456789")
        self.assertEqual(normalize_phone_number("+۹۸۹۱۲۳۴۵۶۷۸۹"), "09123456789")

    def test_normalize_with_0098_prefix(self):
        self.assertEqual(normalize_phone_number("00989123456789"), "09123456789")

    def test_normalize_with_98_prefix(self):
        self.assertEqual(normalize_phone_number("989123456789"), "09123456789")

    def test_normalize_without_leading_zero(self):
        self.assertEqual(normalize_phone_number("9123456789"), "09123456789")

    def test_normalize_with_formatting_spaces_and_dashes(self):
        self.assertEqual(normalize_phone_number("0912-345-6789"), "09123456789")
        self.assertEqual(normalize_phone_number("0912 345 6789"), "09123456789")
        self.assertEqual(normalize_phone_number("(+98) 912 345 6789"), "09123456789")

    def test_invalid_phone_numbers(self):
        invalid_numbers = [
            "",
            None,
            "02188888888",      # Tehran landline
            "091234567",        # Too short
            "0912345678901",    # Too long
            "abcdefghijk",      # Letters
            "0900000000a",      # Contains letter
            "+14155552671",     # US number
        ]
        for num in invalid_numbers:
            with self.subTest(phone=num):
                self.assertFalse(is_valid_iranian_mobile(num))
                with self.assertRaises(ValidationError):
                    normalize_phone_number(num)
                with self.assertRaises(ValidationError):
                    validate_iranian_mobile(num)


class MessageFormattingTest(TestCase):
    def test_registered_user_with_full_name(self):
        user = User(first_name="علی", last_name="رضایی", username="ali_r")
        msg = format_personalized_message(user, "سفارش شما آماده تحویل است.")
        expected = "علی رضایی عزیز\nسفارش شما آماده تحویل است."
        self.assertEqual(msg, expected)

    def test_registered_user_with_first_name_only(self):
        user = User(first_name="مریم", last_name="", username="maryam")
        msg = format_personalized_message(user, "کد تخفیف شما ارسال شد.")
        expected = "مریم عزیز\nکد تخفیف شما ارسال شد."
        self.assertEqual(msg, expected)

    def test_registered_user_missing_name_fallback(self):
        user = User(first_name="", last_name="", username="user123")
        msg = format_personalized_message(user, "سفارش شما آماده تحویل است.")
        expected = "کاربر گرامی\nسفارش شما آماده تحویل است."
        self.assertEqual(msg, expected)

    def test_calculate_sms_parts(self):
        self.assertEqual(calculate_sms_parts(""), 0)
        self.assertEqual(calculate_sms_parts("سلام"), 1)
        self.assertEqual(calculate_sms_parts("a" * 70), 1)
        self.assertEqual(calculate_sms_parts("a" * 71), 2)
        self.assertEqual(calculate_sms_parts("a" * 137), 2)
        self.assertEqual(calculate_sms_parts("a" * 138), 3)

