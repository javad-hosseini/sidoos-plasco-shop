"""Patch CKEditor 5 upload handler to auto-convert images to WebP."""
from utils.images import convert_image_to_webp

_patched = False


def patch_ckeditor_upload():
    """Apply the monkey-patch. Call once at app startup via AppConfig.ready()."""
    global _patched
    if _patched:
        return

    from django_ckeditor_5 import storage_utils

    _original_handle = storage_utils.handle_uploaded_file

    def _webp_handle_uploaded_file(f):
        """Convert the uploaded file to WebP before handing it to the original handler."""
        webp_file, new_name = convert_image_to_webp(f)
        if webp_file:
            webp_file.name = new_name
            return _original_handle(webp_file)
        return _original_handle(f)

    storage_utils.handle_uploaded_file = _webp_handle_uploaded_file
    _patched = True
