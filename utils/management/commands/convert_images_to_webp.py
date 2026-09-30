"""
Management command: convert all existing media images to WebP.

Usage:
    python manage.py convert_images_to_webp                          # dry run
    python manage.py convert_images_to_webp --execute                # convert + delete originals
    python manage.py convert_images_to_webp --execute --keep-originals
"""
import os
import re

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image


# ---------- configuration ----------

# Model ImageField references to update in the database.
# (app_label, model_name, [field_names])
IMAGE_FIELD_MAP = [
    ('blogs', 'Article', ['featured_image', 'og_image']),
    ('home', 'HeroSlide', ['background_image']),
    ('home', 'FeaturedCategory', ['image']),
    ('products', 'Product', ['cover_image', 'og_image']),
    ('products', 'ProductImage', ['image']),
]

# CKEditor HTML content fields whose markup may contain image paths.
# (app_label, model_name, [html_field_names])
HTML_CONTENT_FIELDS = [
    ('blogs', 'Article', ['content']),
    ('products', 'Product', ['description']),
]

CONVERTIBLE = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.jpe'}

# Regex that matches image extensions inside src="..." attributes
# in CKEditor HTML content. Captures the full path and the extension.
_IMG_SRC_RE = re.compile(
    r'(src=["\'])((?:(?:/media/)|(?:media/))\S+?)(\.(?:jpg|jpeg|png|gif|bmp|tiff|jpe))(["\'])',
    re.IGNORECASE,
)


def _is_animated_gif(filepath):
    """Return True if *filepath* is an animated GIF."""
    try:
        with Image.open(filepath) as img:
            if getattr(img, 'is_animated', False) or getattr(img, 'n_frames', 1) > 1:
                return True
            try:
                img.seek(1)
                return True
            except (EOFError, ValueError):
                return False
    except Exception:
        return False


class Command(BaseCommand):
    help = 'Convert all existing media images to WebP format and update DB references.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--execute', action='store_true',
            help='Actually perform conversions (default is dry run).',
        )
        parser.add_argument(
            '--keep-originals', action='store_true',
            help='Keep original files after conversion.',
        )
        parser.add_argument(
            '--quality', type=int, default=80,
            help='WebP quality 1-100 (default: 80).',
        )

    # ------------------------------------------------------------------ #
    #  Main entry point
    # ------------------------------------------------------------------ #
    def log(self, msg, style_func=None):
        out_msg = style_func(msg) if style_func else msg
        try:
            self.stdout.write(out_msg)
        except (UnicodeEncodeError, Exception):
            encoding = getattr(self.stdout, 'encoding', 'utf-8') or 'utf-8'
            safe_text = str(msg).encode(encoding, errors='replace').decode(encoding)
            self.stdout.write(style_func(safe_text) if style_func else safe_text)

    def handle(self, *args, **options):
        import sys
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass
        if hasattr(sys.stderr, 'reconfigure'):
            try:
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass

        self.execute_mode = options['execute']
        self.keep_originals = options['keep_originals']
        self.quality = options['quality']
        self.converted_map = {}  # old_relative_path -> new_relative_path

        media_root = str(settings.MEDIA_ROOT)

        if not self.execute_mode:
            self.log(
                '\n  DRY RUN - no files will be modified. '
                'Pass --execute to perform actual conversion.\n',
                self.style.WARNING,
            )

        # Phase 1: convert files on disk
        self._phase1_convert_files(media_root)

        # Phase 2: update ImageField DB values
        self._phase2_update_imagefields()

        # Phase 3: update CKEditor HTML content
        self._phase3_update_html_content()

        # Phase 4: optionally delete originals
        if not self.keep_originals:
            self._phase4_delete_originals(media_root)

        self.log(
            f'\n  Done. {len(self.converted_map)} image(s) '
            f'{"converted" if self.execute_mode else "would be converted"}.\n',
            self.style.SUCCESS,
        )

    # ------------------------------------------------------------------ #
    #  Phase 1: walk media/ and convert files on disk
    # ------------------------------------------------------------------ #
    def _phase1_convert_files(self, media_root):
        self.log('\n--- Phase 1: Converting files on disk ---')
        count = 0
        skipped_animated = 0

        for dirpath, _dirnames, filenames in os.walk(media_root):
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in CONVERTIBLE:
                    continue

                src_abs = os.path.join(dirpath, fname)
                new_fname = os.path.splitext(fname)[0] + '.webp'
                dst_abs = os.path.join(dirpath, new_fname)

                # Skip animated GIFs
                if ext == '.gif' and _is_animated_gif(src_abs):
                    skipped_animated += 1
                    self.log(f'  SKIP (animated GIF): {src_abs}')
                    continue

                # Build relative paths for the DB update map
                src_rel = os.path.relpath(src_abs, media_root).replace('\\', '/')
                dst_rel = os.path.relpath(dst_abs, media_root).replace('\\', '/')
                self.converted_map[src_rel] = dst_rel

                if self.execute_mode:
                    try:
                        with Image.open(src_abs) as img:
                            if img.mode in ('RGBA', 'LA') or (
                                img.mode == 'P' and 'transparency' in img.info
                            ):
                                img = img.convert('RGBA')
                            else:
                                img = img.convert('RGB')
                            img.save(dst_abs, 'WEBP', quality=self.quality, method=4)
                        count += 1
                    except Exception as exc:
                        self.log(
                            f'  ERROR converting {src_abs}: {exc}',
                            self.style.ERROR,
                        )
                        self.converted_map.pop(src_rel, None)
                else:
                    self.log(f'  {src_rel} -> {dst_rel}')
                    count += 1

        self.log(
            f'  Files {"converted" if self.execute_mode else "to convert"}: {count}'
        )
        if skipped_animated:
            self.log(f'  Skipped (animated GIFs): {skipped_animated}')

    # ------------------------------------------------------------------ #
    #  Phase 2: update ImageField values in the database
    # ------------------------------------------------------------------ #
    def _phase2_update_imagefields(self):
        self.log('\n--- Phase 2: Updating ImageField DB values ---')
        updated = 0

        for app_label, model_name, field_names in IMAGE_FIELD_MAP:
            Model = apps.get_model(app_label, model_name)
            for obj in Model.objects.all().iterator():
                changed = False
                for field_name in field_names:
                    value = getattr(obj, field_name)
                    if not value or not value.name:
                        continue
                    old_name = value.name.replace('\\', '/')
                    if old_name in self.converted_map:
                        new_name = self.converted_map[old_name]
                        if self.execute_mode:
                            setattr(obj, field_name, new_name)
                            changed = True
                        else:
                            self.log(
                                f'  {model_name}.{field_name} pk={obj.pk}: '
                                f'{old_name} -> {new_name}'
                            )
                            updated += 1
                if changed and self.execute_mode:
                    # Use update_fields to avoid triggering full_clean / save hooks
                    try:
                        Model.objects.filter(pk=obj.pk).update(
                            **{fn: getattr(obj, fn) for fn in field_names
                               if getattr(obj, fn)}
                        )
                        updated += 1
                    except Exception as exc:
                        self.log(
                            f'  ERROR updating {model_name} pk={obj.pk}: {exc}',
                            self.style.ERROR,
                        )

        self.log(
            f'  DB records {"updated" if self.execute_mode else "to update"}: {updated}'
        )

    # ------------------------------------------------------------------ #
    #  Phase 3: update hardcoded image paths in CKEditor HTML fields
    # ------------------------------------------------------------------ #
    def _phase3_update_html_content(self):
        self.log('\n--- Phase 3: Updating CKEditor HTML content ---')
        updated = 0

        for app_label, model_name, field_names in HTML_CONTENT_FIELDS:
            Model = apps.get_model(app_label, model_name)
            for obj in Model.objects.all().iterator():
                changed = False
                update_kwargs = {}
                for field_name in field_names:
                    html = getattr(obj, field_name) or ''
                    if not html:
                        continue

                    def _replace_ext(match):
                        prefix = match.group(1)     # src="
                        path = match.group(2)       # /media/uploads/photo
                        old_ext = match.group(3)    # .jpg
                        quote = match.group(4)      # "
                        return f'{prefix}{path}.webp{quote}'

                    new_html = _IMG_SRC_RE.sub(_replace_ext, html)
                    if new_html != html:
                        if self.execute_mode:
                            update_kwargs[field_name] = new_html
                            changed = True
                        else:
                            # Count replacements
                            n = len(_IMG_SRC_RE.findall(html))
                            self.log(
                                f'  {model_name}.{field_name} pk={obj.pk}: '
                                f'{n} image URL(s) to update'
                            )
                            updated += 1

                if changed and self.execute_mode:
                    try:
                        Model.objects.filter(pk=obj.pk).update(**update_kwargs)
                        updated += 1
                    except Exception as exc:
                        self.log(
                            f'  ERROR updating HTML in {model_name} '
                            f'pk={obj.pk}: {exc}',
                            self.style.ERROR,
                        )

        self.log(
            f'  HTML fields {"updated" if self.execute_mode else "to update"}: {updated}'
        )

    # ------------------------------------------------------------------ #
    #  Phase 4: delete original (non-WebP) files
    # ------------------------------------------------------------------ #
    def _phase4_delete_originals(self, media_root):
        self.log('\n--- Phase 4: Deleting original files ---')
        deleted = 0

        for old_rel in self.converted_map:
            old_abs = os.path.join(media_root, old_rel.replace('/', os.sep))
            if self.execute_mode:
                try:
                    if os.path.exists(old_abs):
                        os.remove(old_abs)
                        deleted += 1
                except Exception as exc:
                    self.log(
                        f'  ERROR deleting {old_abs}: {exc}',
                        self.style.ERROR,
                    )
            else:
                self.log(f'  DELETE: {old_rel}')
                deleted += 1

        self.log(
            f'  Files {"deleted" if self.execute_mode else "to delete"}: {deleted}'
        )
