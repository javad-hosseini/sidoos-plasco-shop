"""
Template filters for the blogs app.

Responsibility:
    Exposes `apps.blogs.utils` helpers (Jalali date formatting, Persian
    digit conversion) as Django template filters, so templates can format
    dates and numbers without embedding conversion logic inline.
"""

from django import template

from apps.blogs.utils import format_jalali_date, to_persian_digits

register = template.Library()


@register.filter(name="jalali_date")
def jalali_date(value):
    """Format a Gregorian datetime as a Persian (Jalali) date string."""
    return format_jalali_date(value)


@register.filter(name="persian_digits")
def persian_digits(value):
    """Convert Western digits in a value to Persian digits."""
    return to_persian_digits(value)
