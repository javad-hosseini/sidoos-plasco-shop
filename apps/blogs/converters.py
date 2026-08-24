"""
Custom Django path converters for the blogs app.

Responsibility:
    The `Article.slug` field stores Unicode (Persian) text, not ASCII-only
    slugs. Django's built-in `<slug:...>` path converter only matches
    `[-a-zA-Z0-9_]+`, so it would 404 on any Persian slug (e.g.
    "راهنمای-خرید-گلدان-پلاستیکی"). This module defines a converter that
    accepts any non-slash character instead, so Persian article URLs
    resolve correctly.

Architectural note:
    This converter deliberately does NOT perform any manual URL-encoding
    or decoding. Django/urllib already handles percent-encoding for
    Unicode path segments at the WSGI/ASGI layer, and manually calling
    `quote()`/`unquote()` in view or template code has previously caused
    production 404s on this project (mismatched encoding between the
    browser, web server, and Django). Keep it that way.
"""

from django.urls.converters import StringConverter


class UnicodeSlugConverter(StringConverter):
    """
    Path converter that matches any non-empty, non-slash path segment.

    Used for article slugs, which may contain Persian/Unicode characters.
    Registered under the name 'unicode_slug' (see apps/blogs/urls.py).
    """

    # Same permissive pattern as Django's built-in `str` converter:
    # any character except the path separator ("/").
    regex = "[^/]+"
