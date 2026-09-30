"""Utility for converting uploaded images to WebP format."""
import os
from io import BytesIO

from PIL import Image
from django.core.files.base import ContentFile


# Formats we convert (lowercase). Skip already-webp and non-image types.
CONVERTIBLE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.jpe'}

# WebP quality (80 is a good balance of size vs quality)
WEBP_QUALITY = 80


def is_animated_gif(img):
    """Check if a PIL Image is an animated GIF."""
    try:
        if getattr(img, 'is_animated', False) or getattr(img, 'n_frames', 1) > 1:
            return True
        try:
            curr = img.tell()
            img.seek(1)
            img.seek(curr)
            return True
        except (EOFError, ValueError):
            return False
    except Exception:
        return False


def convert_image_to_webp(image_file, quality=WEBP_QUALITY):
    """
    Convert an in-memory image file to WebP format.

    Skips animated GIFs (preserves them as-is).

    Args:
        image_file: A Django File/InMemoryUploadedFile with image data.
        quality: WebP quality (1-100). Default 80.

    Returns:
        A tuple of (ContentFile with WebP data, new_filename) if converted,
        or (None, None) if the file doesn't need conversion (already WebP,
        not an image, or is an animated GIF).
    """
    name = image_file.name if hasattr(image_file, 'name') else ''
    ext = os.path.splitext(name)[1].lower()

    if ext not in CONVERTIBLE_EXTENSIONS:
        return None, None

    image_file.seek(0)
    img = Image.open(image_file)

    # Skip animated GIFs — WebP can technically hold animation but
    # re-encoding may degrade quality and increase processing time.
    if ext == '.gif' and is_animated_gif(img):
        image_file.seek(0)
        return None, None

    # Convert palette/CMYK/etc. to RGB(A) for WebP compatibility
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        img = img.convert('RGBA')
    else:
        img = img.convert('RGB')

    buffer = BytesIO()
    img.save(buffer, format='WEBP', quality=quality, method=4)
    buffer.seek(0)

    new_name = os.path.splitext(name)[0] + '.webp'
    return ContentFile(buffer.read(), name=os.path.basename(new_name)), new_name


def convert_imagefield_to_webp(instance, field_name):
    """
    Convert a model instance's ImageField to WebP before saving.

    Call this in the model's save() method BEFORE super().save().
    Only converts if the field has a new (unsaved) file upload.

    Args:
        instance: The model instance.
        field_name: Name of the ImageField attribute.
    """
    field_file = getattr(instance, field_name)
    if not field_file or not field_file.name:
        return

    # Only convert if the file is a new upload (not yet committed to storage).
    # A committed file is one already on disk from a previous save.
    if not getattr(field_file, 'committed', True) or (
        hasattr(field_file, 'file')
        and hasattr(field_file.file, 'content_type')
    ):
        ext = os.path.splitext(field_file.name)[1].lower()
        if ext not in CONVERTIBLE_EXTENSIONS:
            return

        webp_file, new_name = convert_image_to_webp(field_file)
        if webp_file:
            # Replace the field file with the WebP version.
            # save=False prevents a recursive Model.save() call.
            field_file.save(new_name, webp_file, save=False)
