# Sidoos Blogs App Documentation

## Overview

The `blogs` app manages the Sidoos Magazine / article system. It provides:

- An `Article` model storing Persian/Unicode content, tags, SEO metadata, and publication status.
- Admin interface for content managers (non‑technical users).
- Article listing view (detail view to be implemented later).
- Custom path converter for Persian slugs.
- Template filters for Jalali dates and Persian digits.

## File Structure

| File | Purpose |
|------|---------|
| `models.py` | Defines the `Article` model and its fields. |
| `admin.py` | Django admin configuration for `Article` and `Tag`. |
| `views.py` | Article listing page view (`article_list`). |
| `urls.py` | URL patterns for the blogs app (imports `converters`). |
| `converters.py` | Custom URL path converter for Unicode slugs. |
| `utils.py` | Helper functions for Jalali date formatting and Persian digit conversion. |
| `templatetags/blog_extras.py` | Template filters wrapping `utils.py` functions. |
| `apps.py` | Django app configuration class. |
| `tests.py` | Unit tests for the `Article` model. |
| `migrations/` | Database migration files (initial + CKEditor field alteration). |

---

## Detailed File Descriptions

### `models.py`

Contains the `Article` model – the core data entity for blog posts.

**Key classes / functions:**

- `class Article(models.Model)` – Represents a magazine article with content, tags, SEO, and publication data.

### `admin.py`

Configures the Django admin interface for `Article` and `Tag`.

**Key classes / functions:**

- `class PublishedFilter` – Custom list filter for publication status (published / draft / scheduled).
- `class HasImageFilter` – Custom list filter for articles with or without a featured image.
- `class ArticleAdmin` – Admin interface for `Article` with custom display methods, fieldsets, actions, and save logic.
- `class TagAdmin` – Admin interface for `Tag` with article count.

### `views.py`

Implements the public article listing page.

**Key functions:**

- `def article_list(request)` – Renders `/blogs/` with published articles, paginated (12 per page).

### `urls.py`

Defines URL patterns for the app.

**Key features:**

- Uses custom `unicode_slug` converter for the detail URL (to be implemented later).
- Registers the converter with Django.

### `converters.py`

Defines a custom path converter that accepts Persian/Unicode slugs.

**Key classes / functions:**

- `class UnicodeSlugConverter` – Matches any non‑slash string, allowing Persian characters in slugs.

### `utils.py`

Provides formatting helpers for the presentation layer.

**Key functions:**

- `def to_persian_digits(value)` – Converts Western digits (`0-9`) to Persian digits (`۰-۹`).
- `def format_jalali_date(value)` – Converts a Gregorian datetime to a Persian (Jalali) date string (e.g., `۲۰ مرداد ۱۴۰۵`).

### `templatetags/blog_extras.py`

Registers Django template filters based on `utils.py`.

**Key filters:**

- `jalali_date` – Formats a datetime as a Jalali date.
- `persian_digits` – Converts digits to Persian.

### `apps.py`

Standard Django app configuration.

**Key class:**

- `class BlogsConfig` – Defines app name (`apps.blogs`) and default auto field.

### `tests.py`

Unit tests for model behavior.

**Key class:**

- `class ArticleModelTests` – Tests article creation, slug uniqueness, Persian Unicode slugs, tags, publication logic, and timestamps.

---

## Models – `Article`

| Field | Type | Description |
|-------|------|-------------|
| `title` | `CharField(max_length=200)` | Main article title (Persian). |
| `slug` | `CharField(max_length=255, unique=True)` | URL slug supporting Persian/Unicode characters; spaces are normalized to hyphens. |
| `summary` | `TextField` | Short excerpt shown in cards and listings. |
| `featured_image` | `ImageField(upload_to="blogs/articles/%Y/%m/", null=True, blank=True)` | Cover image for the article. |
| `content` | `CKEditor5Field` (Rich text field) | Full article HTML content, edited with CKEditor 5. |
| `reading_time` | `PositiveIntegerField` | Estimated reading time in minutes (integer, 1–60). |
| `published_at` | `DateTimeField(null=True, blank=True)` | Publication date/time (Gregorian, timezone‑aware). |
| `is_published` | `BooleanField(default=False)` | Controls whether the article is publicly visible. |
| `tags` | `TaggableManager` (django‑taggit) | Many‑to‑many tags for related articles (supports Persian). |
| `meta_title` | `CharField(max_length=200, blank=True)` | SEO title. |
| `meta_description` | `TextField(blank=True)` | SEO meta description. |
| `canonical_url` | `URLField(blank=True)` | Canonical URL for SEO. |
| `og_title` | `CharField(max_length=200, blank=True)` | Open Graph title for social sharing. |
| `og_description` | `TextField(blank=True)` | Open Graph description. |
| `og_image` | `ImageField(upload_to="blogs/og-images/%Y/%m/", null=True, blank=True)` | Image for social sharing. |
| `robots` | `CharField(max_length=50, default="index,follow", blank=True)` | Robots meta tag instructions. |
| `created_at` | `DateTimeField(auto_now_add=True)` | Automatic creation timestamp. |
| `updated_at` | `DateTimeField(auto_now=True)` | Automatic last update timestamp. |

**Model methods:**

- `__str__()` – Returns the article title.
- `clean()` – Validates slug format and publication logic (e.g., published articles require a publication date).
- `save()` – Runs full validation before saving.

---

## Important Notes

### Unicode / Persian Slugs

- The `slug` field is a `CharField`, **not** Django’s `SlugField`, because `SlugField` only accepts ASCII characters.
- The custom `UnicodeSlugConverter` (in `converters.py`) must be used in URL patterns instead of the built‑in `<slug:slug>` converter.
- Never manually call `urllib.parse.quote()` / `unquote()` on slugs – Django and the web server handle encoding automatically.

### Jalali Dates

- Dates are stored as Gregorian `DateTimeField` in the database.
- Display conversion to Jalali is done only in the presentation layer using `jdatetime` (via `utils.py` and template filters).
- Do not store Jalali date strings in the model.

### Tags

- The app uses `django-taggit`; tags support Persian characters.
- The default `Tag` admin is unregistered and replaced with a custom `TagAdmin` that displays article counts.

### CKEditor 5

- The `content` field uses `CKEditor5Field` and is configured via `CKEDITOR_5_CONFIGS` in `settings.py`.
- CKEditor toolbar and RTL settings can be customized there.

### Views

- Currently only `article_list` is implemented.
- The detail view (`article_detail`) is **not yet implemented** – the listing page links to a URL name that will be added later.