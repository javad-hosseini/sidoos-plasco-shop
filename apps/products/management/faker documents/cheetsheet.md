
# Mock Data Commands — Cheat Sheet

## Installation

```bash
pip install faker requests
````

---

## Commands

### 1. Create Categories

```bash
# Create all categories (4 main, ~65 total)
python manage.py seed_categories

# Clear existing categories first
python manage.py seed_categories --clear
```

### 2. Create Products

```bash
# Create 200 products (default)
python manage.py seed_products

# Create specific number
python manage.py seed_products --count=500

# Create in specific category only
python manage.py seed_products --category="گلدان"

# Clear existing products, then create
python manage.py seed_products --clear --count=300
```

### 3. Clear All Mock Data

```bash
# Delete everything (products, categories, images, likes, saves)
python manage.py clear_mock_data
```

---

## One-Liner: Fresh Start

```bash
python manage.py clear_mock_data && python manage.py seed_categories && python manage.py seed_products --count=200
```

---

## Arguments Reference

| Command | Flag | Type | Default | Description |
|---------|------|------|---------|-------------|
| `seed_categories` | `--clear` | flag | `False` | Delete existing categories |
| `seed_products` | `--count` | int | `200` | Number of products |
| `seed_products` | `--clear` | flag | `False` | Delete existing products |
| `seed_products` | `--category` | str | `None` | Filter by category name |

---

## Data Distribution (Default)

| Type | Percentage |
|------|-----------|
| گلدان (Flower Pots) | 35% |
| Other categories | ~21.67% each |

| Status | Percentage |
|--------|-----------|
| Regular price | ~55% |
| On sale | ~30% |
| Call for price | ~15% |

| Flag | Probability |
|------|-------------|
| `published` | 90% |
| `featured_in_special_sales` | 25% |
| `is_featured` | 15% |

---

## Category Depth Distribution

| Depth | Probability |
|-------|-------------|
| Level 1 (main) | 40% |
| Level 2 (sub) | 35% |
| Level 3 (sub-sub) | 20% |
| Level 4 (sub-sub-sub) | 5% |

---

## File Locations

```
apps/products/management/
├── __init__.py
└── commands/
    ├── __init__.py
    ├── seed_categories.py
    ├── seed_products.py
    └── clear_mock_data.py
```

---

## Quick Examples

```bash
# Test with lots of nested categories
python manage.py seed_categories
python manage.py seed_products --count=50

# Test flower pot heavy scenario
python manage.py seed_products --category="گلدان" --count=100

# Test sanitary products
python manage.py seed_products --category="بهداشتی" --count=80

# Reset everything
python manage.py clear_mock_data
```

---

## Price Range

- **Regular:** 50,000 – 5,000,000 Toman
- **On sale:** 70% – 90% of original price

---

## Images

- **Source:** generated locally with Pillow (no network calls)
- **Size:** 800×600

---

## Notes

- Superuser auto-created if missing (`admin` / `admin123`)
- Progress logged every 25 products
- ~2-3 minutes for 200 products (internet dependent)
```