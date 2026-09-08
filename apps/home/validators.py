"""
File validation utilities for the home application.

Currently used by the downloadable price-list files (PriceList), which are
uploaded by staff through the Django admin and served back to authenticated
users through a controlled download view.

Security considerations mirror apps.support.validators (the project's
existing convention) and go one step further, because these files are
offered as downloads to every logged-in customer:

- The extension allow-list is closed (PDF/JPG/JPEG/PNG only).
- The declared MIME type must agree with the extension.
- The file's own leading bytes (magic number) must agree too, so a
  renamed executable/script cannot pass as a PDF or an image.
- Images are additionally decoded with PIL.

Extension and browser-supplied content type are both attacker-controlled
for an untrusted uploader, so neither is ever trusted on its own.
"""

import os

from django.core.exceptions import ValidationError
from PIL import Image


# Extension -> the MIME types a browser may legitimately report for it.
ALLOWED_PRICE_LIST_TYPES = {
    ".pdf": {"application/pdf"},
    ".jpg": {"image/jpeg", "image/jpg", "image/pjpeg"},
    ".jpeg": {"image/jpeg", "image/jpg", "image/pjpeg"},
    ".png": {"image/png", "image/x-png"},
}

ALLOWED_PRICE_LIST_EXTENSIONS = frozenset(ALLOWED_PRICE_LIST_TYPES)

# Extension -> the byte signatures the file itself must start with.
_MAGIC_NUMBERS = {
    ".pdf": (b"%PDF-",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
}

_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png"})

# Price lists are catalogue documents, so they are allowed to be larger
# than a support attachment (10 MB) but not unbounded.
MAX_PRICE_LIST_SIZE = 20 * 1024 * 1024  # 20 MB


def get_file_extension(filename):
    """Return the lowercase extension of `filename`, including the dot."""
    return os.path.splitext(filename or "")[1].lower()


def _read_head(file, length):
    """Read the first `length` bytes of `file`, leaving the pointer at 0."""
    try:
        file.seek(0)
        head = file.read(length)
    finally:
        file.seek(0)
    return head


def validate_price_list_file(file):
    """
    Validate an uploaded price-list file.

    Checks, in order: extension allow-list, declared MIME type, size, and
    the file's actual leading bytes; images are then decoded to confirm
    they really are images.

    Raises:
        ValidationError: if any check fails.

    Returns:
        str: the normalised extension that was accepted.
    """
    extension = get_file_extension(getattr(file, "name", ""))

    if extension not in ALLOWED_PRICE_LIST_TYPES:
        raise ValidationError(
            "فرمت فایل مجاز نیست. فقط فایل‌های PDF، JPG، JPEG و PNG پذیرفته می‌شوند."
        )

    content_type = getattr(file, "content_type", None)
    if content_type and content_type.lower() not in ALLOWED_PRICE_LIST_TYPES[extension]:
        raise ValidationError(
            f"نوع فایل «{content_type}» با پسوند «{extension}» مطابقت ندارد."
        )

    size = getattr(file, "size", None)
    if size is not None and size > MAX_PRICE_LIST_SIZE:
        raise ValidationError(
            f"حجم فایل نباید بیشتر از {MAX_PRICE_LIST_SIZE // (1024 * 1024)} مگابایت باشد."
        )

    signatures = _MAGIC_NUMBERS[extension]
    head = _read_head(file, max(len(sig) for sig in signatures))
    if not any(head.startswith(sig) for sig in signatures):
        raise ValidationError(
            "محتوای فایل با پسوند آن مطابقت ندارد. فایل سالم و معتبر بارگذاری کنید."
        )

    if extension in _IMAGE_EXTENSIONS:
        try:
            image = Image.open(file)
            image.verify()
        except Exception:
            raise ValidationError("فایل تصویری معتبر نیست.")
        finally:
            file.seek(0)

    return extension
