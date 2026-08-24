"""
Presentation-layer helpers for the blogs app.

Responsibility:
    Converts Gregorian datetimes (as stored in `Article.published_at`) into
    human-readable Jalali (Persian) date strings with Persian digits, and
    converts arbitrary integers/strings to Persian digits (e.g. for
    reading time).

Architectural decision:
    This conversion is intentionally kept out of the `Article` model and
    out of the database. The DB continues to store Gregorian `DateTimeField`
    values; Jalali display is computed on demand wherever it's needed
    (template filters, views). This keeps the model storage-format-agnostic
    and avoids maintaining a second, redundant date field.

    Requires the third-party `jdatetime` package
    (pip install jdatetime).
"""

import jdatetime

# Persian month names, in order (index 0 = فروردین).
PERSIAN_MONTH_NAMES = [
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
]

# Translation table for Western Arabic digits -> Persian digits.
_PERSIAN_DIGIT_MAP = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def to_persian_digits(value) -> str:
    """
    Convert any value containing Western digits (0-9) into Persian digits.

    Accepts ints, strings, or anything str()-able.
    """
    return str(value).translate(_PERSIAN_DIGIT_MAP)


def format_jalali_date(value) -> str:
    """
    Format a Gregorian datetime/date as a Persian date string.

    Example:
        2026-08-11 (Gregorian) -> "۲۰ مرداد ۱۴۰۵"

    Returns an empty string for falsy input (e.g. unpublished articles
    with no `published_at`), so templates can safely call this
    unconditionally.
    """
    if not value:
        return ""

    jalali = jdatetime.date.fromgregorian(date=value.date() if hasattr(value, "date") else value)

    day = to_persian_digits(jalali.day)
    month_name = PERSIAN_MONTH_NAMES[jalali.month - 1]
    year = to_persian_digits(jalali.year)

    return f"{day} {month_name} {year}"
