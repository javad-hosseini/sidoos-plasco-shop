"""
Centralized phone number normalization, validation, and SMS formatting utilities.

This module serves as the single source of truth for Iranian mobile phone
validation and normalization across the application.
"""

import re
from django.core.exceptions import ValidationError


PERSIAN_ARABIC_DIGITS = "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩"
ASCII_DIGITS = "01234567890123456789"
DIGIT_TRANSLATION_TABLE = str.maketrans(PERSIAN_ARABIC_DIGITS, ASCII_DIGITS)

IRANIAN_MOBILE_REGEX = re.compile(r"^09\d{9}$")


def normalize_phone_number(raw_phone: str) -> str:
    """
    Normalize an input phone string into canonical Iranian mobile format: 09xxxxxxxxx.

    Handles:
    - Persian and Arabic numerals (e.g. ۰۹۱۲۳۴۵۶۷۸۹ -> 09123456789)
    - International prefixes: +98, 0098, 98
    - Missing leading zero: 9123456789
    - Formatting characters: spaces, hyphens, parentheses, pluses

    Returns:
        str: 11-digit canonical mobile string starting with '09'.

    Raises:
        ValidationError: If the input cannot be resolved to a valid Iranian mobile.
    """
    if not raw_phone:
        raise ValidationError("شماره موبایل نمی‌تواند خالی باشد.")

    # 1. Convert Persian/Arabic digits to ASCII
    text = str(raw_phone).strip().translate(DIGIT_TRANSLATION_TABLE)

    # 2. Extract only digits and leading plus
    has_plus = text.startswith("+")
    clean = "".join(ch for ch in text if ch.isdigit())

    # 3. Handle prefixes
    # +989...
    if has_plus and clean.startswith("98"):
        clean = clean[2:]
    # 00989...
    elif clean.startswith("0098"):
        clean = clean[4:]
    # 989... (12 digits)
    elif clean.startswith("98") and len(clean) == 12:
        clean = clean[2:]

    # If it starts with 9 and has 10 digits (e.g. 9123456789) -> prepend 0
    if clean.startswith("9") and len(clean) == 10:
        clean = "0" + clean

    # 4. Final validation against 09xxxxxxxxx
    if not IRANIAN_MOBILE_REGEX.match(clean):
        raise ValidationError(
            f"شماره موبایل '{raw_phone}' نامعتبر است. شماره موبایل معتبر باید ۱۱ رقم بوده و با ۰۹ شروع شود."
        )

    return clean


def is_valid_iranian_mobile(raw_phone: str) -> bool:
    """
    Check whether a phone number is a valid Iranian mobile number.

    Returns:
        bool: True if valid, False otherwise.
    """
    try:
        normalize_phone_number(raw_phone)
        return True
    except (ValidationError, TypeError, ValueError):
        return False


def validate_iranian_mobile(value: str) -> None:
    """
    Django field and form validator for Iranian mobile numbers.
    """
    normalize_phone_number(value)


def format_personalized_message(user, base_message: str) -> str:
    """
    Format a personalized SMS message for a registered site user.

    Rule:
    - If user has a non-empty full name:
      {user full name} عزیز
      {message body}
    - If user has no name (missing/blank first and last name):
      کاربر گرامی
      {message body}

    Args:
        user: The User instance.
        base_message: The admin-composed text body.

    Returns:
        str: The final personalized message.
    """
    base_text = (base_message or "").strip()

    full_name = ""
    if hasattr(user, "get_full_name"):
        full_name = user.get_full_name().strip()
    elif hasattr(user, "first_name") or hasattr(user, "last_name"):
        first = getattr(user, "first_name", "") or ""
        last = getattr(user, "last_name", "") or ""
        full_name = f"{first} {last}".strip()

    if full_name:
        greeting = f"{full_name} عزیز"
    else:
        greeting = "کاربر گرامی"

    return f"{greeting}\n{base_text}"


def calculate_sms_parts(text: str) -> int:
    """
    Calculate the number of SMS segments for a given text.
    Standard Iranian SMS encoding (Unicode / Persian):
    - 1 part: up to 70 characters
    - Subsequent parts: 67 characters each
    """
    if not text:
        return 0
    length = len(text)
    if length <= 70:
        return 1
    return 1 + (length - 70 + 66) // 67

