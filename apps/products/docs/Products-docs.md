# Sidoos Products App Documentation

## Overview

The `products` app manages the e-commerce product catalog for the Sidoos Plasco Shop. It provides:

- A `Product` model storing product details, pricing, media, and availability status.
- A hierarchical `Category` model (categories + subcategories) for product classification.
- `ProductImage` model for managing a gallery of product images.
- `ProductSave` and `ProductLike` models for tracking user interactions (save/like functionality).
- Comprehensive admin interface for non-technical staff to manage products.
- Django-taggit integration for flexible product categorization.
- Automatic discount percentage calculation based on sale pricing.
- "Call for Price" feature for products with negotiable pricing.

## File Structure

| File | Purpose |
|------|---------|
| `models.py` | Defines `Category`, `Product`, `ProductImage`, `ProductSave`, and `ProductLike` models. |
| `converters.py` | Defines a Unicode-friendly slug converter for product detail URLs. |
| `admin.py` | Django admin configuration with custom displays, filters, and inlines. |
| `views.py` | Product listing, detail, and special sales views. |
| `urls.py` | URL patterns: `/`, `/<slug>/`, `/special-sales/`, and category routes. |
| `templates/products/` | HTML templates for product pages (product_list, product_detail, special_sales). |
| `apps.py` | Django app configuration class. |
| `tests.py` | Unit tests for product models. |
| `migrations/` | Database migration files (initial + CKEditor field alteration). |

---

## Detailed File Descriptions

### `models.py`

Contains five core models: `Category`, `Product`, `ProductImage`, `ProductSave`, and `ProductLike`.

**Key classes:**

- `class Product(models.Model)` – Main product entity with pricing, media, status flags, and user relationships.
- `class Category(models.Model)` – Hierarchical category tree with optional parent for nested subcategories.
- `class ProductImage(models.Model)` – Gallery image for products with ordering support.
- `class ProductSave(models.Model)` – Tracks products saved by users (many-to-many with constraints).
- `class ProductLike(models.Model)` – Tracks products liked by users (many-to-many with constraints).

### `admin.py`

Configures the Django admin interface for all product-related models.

**Key classes:**

- `class ProductImageInline` – Inline admin for managing product images directly from the `Product` admin.
- `class ProductAdmin` – Admin interface for `Product` with custom displays for pricing, discounts, and status.
- `class ProductImageAdmin` – Admin interface for `ProductImage` with thumbnail preview.
- `class ProductSaveAdmin` – Read-only admin for `ProductSave` with filtering by user and date.
- `class ProductLikeAdmin` – Read-only admin for `ProductLike` with filtering by user and date.

### `views.py`

Implements the public product listing, detail, and special sales pages.

**Key functions:**

- `def product_list(request)` – Renders `/products/` with all published products, paginated (12 per page), and computes `can_view_price` for template price gating.
- `def product_detail(request, slug)` – Renders `/products/<slug>/` with full product details, gallery, tags, user interaction status, and `can_view_price`.
- `def special_sales(request)` – Renders `/products/special-sales/` with featured sale products, paginated (12 per page), and `can_view_price`.
- `def category_products(request, slug)` – Renders category-filtered products (including descendants) with the same price-visibility rules.
- `def toggle_save(request, product_id)` – Authenticated POST endpoint to toggle saved state and return JSON.
- `def toggle_like(request, product_id)` – Authenticated POST endpoint to toggle liked state and return JSON.

### `urls.py`

Defines URL patterns for the app.

**Key routes:**

- `''` → `product_list` – All published products
- `'special-sales/'` → `special_sales` – Featured sale products
- `'categories/'` → `category_list` – All categories and subcategories
- `'categories/new/'` → `category_create` – Create a category or subcategory
- `'categories/<slug>/'` → `category_products` – Products in category + descendants
- `'api/<int:product_id>/save/'` → `toggle_save` – Toggle save state (POST, login required)
- `'api/<int:product_id>/like/'` → `toggle_like` – Toggle like state (POST, login required)
- `'<unicode_slug:slug>/'` → `product_detail` – Individual product page (Unicode/Persian-safe)

### `apps.py`

Standard Django app configuration.

**Key class:**

- `class ProductsConfig` – Defines app name (`apps.products`) and default auto field.

### `tests.py`

Unit tests for product model behavior and constraints.

---

## Models – Detailed Reference

### `Product` Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | `BigAutoField (PK)` | Auto-incrementing primary key. |
| `name` | `CharField(max_length=255, unique=True)` | Product name (must be unique). |
| `slug` | `SlugField(max_length=255, unique=True, blank=True, allow_unicode=True)` | URL-friendly slug; auto-generated from name using Unicode-aware `slugify()`. |
| `description` | `CKEditor5Field` (Rich text) | Detailed product description with rich text formatting (bold, italic, links, images, lists, etc.). |
| `price` | `DecimalField(max_digits=10, decimal_places=2)` | Regular retail price. Must be ≥ 0. Set to 0 if `call_for_price=True`. |
| `on_sale_price` | `DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)` | Optional discounted sale price. Must be ≥ 0 if provided. |
| `cover_image` | `ImageField(upload_to='products/covers/')` | Main product image. |
| `call_for_price` | `BooleanField(default=False)` | If `True`, price is hidden from website; price stored as 0 internally. |
| `published` | `BooleanField(default=False)` | Controls product visibility on the website. |
| `featured_in_special_sales` | `BooleanField(default=False)` | If `True`, product appears in the "Special Sales" section. |
| `creator` | `ForeignKey(User, null=True, related_name='products_created')` | User who created the product. |
| `tags` | `TaggableManager` (django-taggit) | Flexible many-to-many tags for categorization (e.g., "plastic", "durable", "indoor"). |
| `created_at` | `DateTimeField(auto_now_add=True)` | Automatic creation timestamp (UTC). |
| `updated_at` | `DateTimeField(auto_now=True)` | Automatic last update timestamp (UTC). |

**Model methods:**

- `save()` – Overridden to:
  - Auto-generate a Unicode-aware `slug` from `name` if not provided (`slugify(..., allow_unicode=True)`).
  - Guarantee slug uniqueness by appending a numeric suffix (`-2`, `-3`, ...).
  - Use `product` as fallback base slug if the name produces an empty slug.
  - Set `price = 0` if `call_for_price=True` (internal representation).
  
- `get_discount_percentage()` – Returns the discount percentage as a float if `on_sale_price` is set:
  - Formula: `((price - on_sale_price) / price) * 100`
  - Returns `None` if no sale price is set or price is 0.
  - Example: Price $100, Sale $70 → 30.0% discount.

- `__str__()` – Returns the product name.

**Indexes:**

- `published` – For efficient filtering of published products.
- `featured_in_special_sales` – For efficient querying of sale products.
- `slug` – For fast lookups by URL slug.

---

### `ProductImage` Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | `BigAutoField (PK)` | Auto-incrementing primary key. |
| `product` | `ForeignKey(Product, CASCADE, related_name='images')` | Parent product; deleted if product is deleted. |
| `image` | `ImageField(upload_to='products/images/')` | Actual image file. |
| `order` | `PositiveIntegerField(default=0)` | Display order within the product's gallery. |
| `created_at` | `DateTimeField(auto_now_add=True)` | Automatic creation timestamp. |

**Model methods:**

- `__str__()` – Returns "Image for {product name}".

**Ordering:** By `order` and `created_at` (ascending).

---

### `ProductSave` Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | `BigAutoField (PK)` | Auto-incrementing primary key. |
| `user` | `ForeignKey(User, CASCADE, related_name='saved_products')` | User who saved the product. |
| `product` | `ForeignKey(Product, CASCADE, related_name='saved_by_users')` | Saved product. |
| `created_at` | `DateTimeField(auto_now_add=True)` | Timestamp when product was saved. |

**Unique Constraint:** `(user, product)` – Prevents the same user from saving the same product twice.

**Model methods:**

- `__str__()` – Returns "{username} saved {product name}".

**Meta:**

- `verbose_name_plural = "Product Saves"` – Proper plural form in admin.

---

### `ProductLike` Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | `BigAutoField (PK)` | Auto-incrementing primary key. |
| `user` | `ForeignKey(User, CASCADE, related_name='liked_products')` | User who liked the product. |
| `product` | `ForeignKey(Product, CASCADE, related_name='liked_by_users')` | Liked product. |
| `created_at` | `DateTimeField(auto_now_add=True)` | Timestamp when product was liked. |

**Unique Constraint:** `(user, product)` – Prevents the same user from liking the same product twice.

**Model methods:**

- `__str__()` – Returns "{username} liked {product name}".

**Meta:**

- `verbose_name_plural = "Product Likes"` – Proper plural form in admin.

---

## Admin Interface Features

### Product Admin

**List Display:**
- Product name
- Price (with "Call for Price" indicator in red if applicable)
- Discount percentage (in green if sale price is set)
- Publication status
- Featured in special sales status
- Creation date

**Filters:**
- By `published` status
- By `featured_in_special_sales` status
- By `call_for_price` flag
- By creation date

**Search:** By product name or description.

**Fieldsets:**
1. **Basic Information** – name, slug, description
2. **Media** – cover_image
3. **Pricing** – price, on_sale_price, call_for_price, discount_percentage (read-only)
4. **Status & Visibility** – published, featured_in_special_sales
5. **Tags & Creator** – tags, creator
6. **Timestamps** (collapsible) – created_at, updated_at (read-only)

**Inlines:**
- `ProductImageInline` – Add/edit up to 3 product images directly from the product admin.

**Custom Methods:**
- `price_display()` – Shows "Call for Price" in red or the actual price.
- `discount_display()` – Shows discount % in green or "–" if no sale.
- `discount_percentage()` – Read-only field showing calculated discount or message.

### ProductImage Admin

**List Display:**
- Product name
- Image order
- Creation date
- Thumbnail preview (50×50px)

**Filters:**
- By creation date
- By product

**Search:** By product name.

### ProductSave & ProductLike Admin

**Read-Only:** Users should not manually create saves/likes; they are created via frontend interactions.

**Features:**
- List display: user, product, timestamp
- Filters by user and date
- Search by username or product name

---

## Important Notes

### Pricing & Discount Calculation

- **Regular Price:** Always stored in `price` field (cannot be NULL).
- **Sale Price:** Optional; if provided, overrides the regular price for display.
- **Call for Price:** If `call_for_price=True`, the `price` is automatically set to 0 in the `save()` method, hiding the price from the website.
- **Price Visibility Rule:** Price values are rendered only when the user is authenticated **and** `user.has_price_access` is `True`.
- **Discount Percentage:** Calculated dynamically via `get_discount_percentage()` method:
  - Only computed if both `price > 0` and `on_sale_price` is set.
  - Returns a rounded float (e.g., 30.0 for 30%).
  - Returns `None` if no sale price is set.

### User Profile Integration

- The account profile page (`/accounts/profile/`) shows the logged-in user's saved and liked products.
- Profile data is sourced from `ProductSave` and `ProductLike` relations and filtered to published products.

### Slug Behavior

- Slugs are auto-generated from product names using Unicode-aware `slugify(..., allow_unicode=True)`.
- Slugs are made unique automatically with numeric suffixes when needed (`product`, `product-2`, ...).
- If slug generation returns empty (for punctuation-only names), the fallback base slug `product` is used.
- Product detail URLs use a Unicode-safe route converter: `/<unicode_slug:slug>/`.

### User Interactions (Saves & Likes)

- Each `ProductSave` and `ProductLike` entry is unique per user per product (enforced by database constraint).
- Attempting to save/like the same product twice raises an `IntegrityError`.
- To toggle a like/save, the frontend should:
  1. Check if a save/like exists for (user, product).
  2. If exists, delete it; if not, create it.

### Tags

- The app uses `django-taggit` for flexible product categorization.
- Tags support Persian and Unicode characters.
- Add tags via `product.tags.add("tag1", "tag2", ...)`.
- Query by tag: `Product.objects.filter(tags__name__in=["plastic", "durable"])`.

### Media Storage

- **Cover Images:** Stored in `media/products/covers/`.
- **Gallery Images:** Stored in `media/products/images/`.
- Pillow library handles image processing; no thumbnail auto-generation is configured.

### Deletion Behavior

- Deleting a `Product` cascades to:
  - All related `ProductImage` records.
  - All related `ProductSave` records.
  - All related `ProductLike` records.
- Deleting a `User` cascades to all their `ProductSave` and `ProductLike` records.

---

## Database Queries (Common Patterns)

### Get all published products:
```python
products = Product.objects.filter(published=True)
```

### Get products in special sales:
```python
sale_products = Product.objects.filter(published=True, featured_in_special_sales=True)
```

### Get products by tag:
```python
plastic_products = Product.objects.filter(tags__name__in=["plastic"])
```

### Get products with a sale price and discount:
```python
discounted = Product.objects.exclude(on_sale_price__isnull=True)
for product in discounted:
    discount = product.get_discount_percentage()
```

### Get products saved by a user:
```python
user_saves = user.saved_products.all()
```

### Get products liked by a user:
```python
user_likes = user.liked_products.all()
```

### Get users who saved a product:
```python
savers = product.saved_by_users.all()
```

### Check if a user saved a product:
```python
is_saved = ProductSave.objects.filter(user=user, product=product).exists()
```

### Toggle a save for a user:
```python
save, created = ProductSave.objects.get_or_create(user=user, product=product)
if not created:
    save.delete()
```

---

## Next Steps for Frontend Integration

1. **Product Listing View** – Display published products with filters, search, and pagination.
2. **Product Detail View** – Show full product details, gallery, tags, and user interactions.
3. **Save/Like Endpoints** – Create API views or form handlers for toggling saves/likes.
4. **Special Sales Section** – Display featured products with discount badges.
5. **Product Search** – Implement tag-based and full-text search.
6. **User Profile** – Show saved and liked products for each user.

---

## Related Configuration

- **Django-taggit:** Pre-installed and configured in `INSTALLED_APPS`.
- **Pillow:** Required for `ImageField` support; listed in `requirements.txt`.
- **Image Upload Path:** Configured to organize files by type (e.g., `products/covers/`).
- **Custom User Model:** `settings.AUTH_USER_MODEL = 'accounts.User'` – Uses a custom `User` model.
