# Sidoos Plasco Shop

Sidoos Plasco Shop is a Django-based B2B wholesale storefront with Persian/RTL-focused UX.  
The current codebase includes product catalog browsing, account login/profile, blog listing, and a ticket-based support workflow.

## Tech Stack

- Python + Django 4.2
- SQLite (development) / PostgreSQL (production mode)
- django-jazzmin (admin UI)
- django-ckeditor-5 (rich text)
- django-taggit (tagging)
- Pillow + jdatetime

## Project Structure

```text
config/               Django settings and root URL config
apps/
  accounts/           Custom user model + custom authentication backend
  products/           Catalog, categories, product detail, save/like APIs
  blogs/              Article model + article listing page
  support/            Ticket system (customer + admin reply workflow)
  home/               Homepage route/template
templates/            Shared and app templates
static/               Source static assets
media/                Uploaded files (product/support/blog content)
```

## Implemented Features

1. **Products**
   - Published product listing and detail pages
   - Special sales page
   - Hierarchical categories (with descendant category filtering)
   - Save/like toggle endpoints for authenticated users
   - Price visibility gate via `user.has_price_access`

2. **Accounts**
   - Custom `User` model (`phone_number`, `has_price_access`)
   - Authentication by username/email/phone
   - Login, logout, and profile page (saved + liked products)

3. **Blogs**
   - Article model with Unicode/Persian slug support
   - Jalali/Persian date helpers
   - Paginated article listing (`/blogs/`)
   - **Note:** article detail route/view is not implemented yet

4. **Support**
   - Ticket creation with 6-digit tracking code
   - Ticket conversation view for ticket owner
   - Turn-based messaging rules enforced in services
   - Attachment validation (JPG/JPEG/PNG/WEBP/PDF + size checks)
   - Custom admin workflow for support replies, close, and reopen

## Requirements

- Python 3.10+ (recommended)
- pip

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create a development env file:

```bash
copy .env.example .env.dev
```

Fill at least:

```env
APP_ENV=development
DEBUG=True
SECRET_KEY=your-secret-key
```

## Environment Configuration

The project uses `.env.dev` and `.env.prod`.

- In `settings.py`, configuration is currently loaded from `.env.dev` by default.
- Database selection is controlled by `APP_ENV`:
  - `APP_ENV=production` -> PostgreSQL (uses `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`)
  - otherwise -> SQLite (`db.sqlite3`)

## Run the Project

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open:

- Site: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/sidoos-administration/`

## Main Routes

- `/` -> home
- `/accounts/login/`, `/accounts/logout/`, `/accounts/profile/`
- `/products/`, `/products/special-sales/`
- `/products/categories/`, `/products/categories/new/`, `/products/categories/<slug>/`
- `/products/<unicode-slug>/`
- `/blogs/`
- `/support/`, `/support/new/`, `/support/tickets/<6-digit-code>/`

## Running Tests

```bash
python manage.py test
```

Or per app:

```bash
python manage.py test apps.products
python manage.py test apps.blogs
python manage.py test apps.support
python manage.py test apps.accounts
python manage.py test apps.home
```

## Notes

- Uploaded files are served from `media/` in debug mode.
- Static source files are in `static/`; collected static output goes to `staticfiles/`.
- CKEditor uploads are stored under `media/content/ckeditor/`.


## Site Routes

```text
/
├── robots.txt
├── sitemap.xml
├── sidoos-administration/
├── ckeditor5/
│
├── /                       → Home
│
├── accounts/
│   ├── login/
│   ├── logout/
│   └── profile/
│
├── blogs/
│   └── /
│
├── products/
│   ├── /
│   ├── special-sales/
│   ├── categories/
│   ├── categories/new/
│   ├── categories/<slug>/
│   ├── api/<product_id>/save/
│   ├── api/<product_id>/like/
│   └── <unicode_slug>/
│
└── support/
    ├── /
    ├── new/
    └── tickets/<tracking_code>/
```