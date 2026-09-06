
# Mock Data Generation System

## Overview

This document describes the mock data generation system for the Sidoos Plasco Shop Django project. The system consists of three management commands that generate realistic test data for categories, products, and allow cleanup of all mock data.

## Prerequisites

### Installation

```bash
pip install faker
pip install requests

````
Add to `requirements.txt`:

```txt
faker>=24.0.0
requests>=2.31.0
```

### Dependencies

- **Faker** (`fa_IR` locale): Generates Persian fake words and content
- **Requests**: Downloads real images from picsum.photos
- **Django Auth**: Uses the superuser as product creator
- **Product Models**: `Category`, `Product`, `ProductImage`, `ProductSave`, `ProductLike`

---

## File Structure

```
apps/products/
├── management/
│   ├── __init__.py
│   └── commands/
│       ├── __init__.py
│       ├── seed_categories.py
│       ├── seed_products.py
│       └── clear_mock_data.py
```

---

## Management Commands

### 1. `seed_categories` — Generate Category Tree

Creates a nested category structure (up to 4 levels deep) based on real product data.

#### Usage

```bash
# Basic usage — creates all categories
python manage.py seed_categories

# Clear existing categories before creating new ones
python manage.py seed_categories --clear
```

#### Category Structure Generated

```
├── محصولات آشپزخانه (Kitchen Products)
│   ├── ابزارآلات آشپزخانه (Kitchen Tools)
│   │   ├── پوست کن (Peelers)
│   │   ├── چاقو تیزکن (Knife Sharpeners)
│   │   ├── جا ادویه (Spice Racks)
│   │   └── نمک پاش (Salt Shakers)
│   ├── ظروف نگهداری (Storage Containers)
│   │   ├── ظرف دربسته (Airtight Containers)
│   │   ├── بطری روغن (Oil Bottles)
│   │   └── ظرف حبوبات (Legume Containers)
│   └── ظروف سرو (Serving Dishes)
│       ├── سینی (Trays)
│       ├── بشقاب (Plates)
│       └── کاسه (Bowls)
│
├── محصولات بهداشتی ساختمانی (Sanitary Building Products)
│   ├── لوازم توالت فرنگی (Toilet Accessories)
│   │   ├── فلوتر (Floaters)
│   │   ├── پمپ تخلیه (Drain Pumps)
│   │   ├── کیت نصب درب (Door Installation Kits)
│   │   └── دکمه تخلیه (Flush Buttons)
│   ├── سیفون‌ها (Siphons)
│   │   ├── سیفون فانتزی (غیر هم سطح)
│   │   ├── سیفون فانتزی (هم سطح)
│   │   ├── سیفون کلاسیک ظرفشویی
│   │   ├── سیفون کششی
│   │   ├── سیفون روشویی
│   │   └── سیفون وان و زیردوشی
│   ├── کفشورها (Floor Drains)
│   │   ├── کفشور پایه بلند
│   │   ├── کفشور پلمپ دار
│   │   └── کفشور خطی
│   ├── سردوش‌ها (Shower Heads)
│   │   ├── سردوش کوچک
│   │   ├── سردوش گرد
│   │   ├── سردوش مربع
│   │   └── سردوش تلفنی
│   └── قطعات و اتصالات (Parts & Fittings)
│       ├── زیرآب
│       ├── واشر
│       ├── پیچ یدکی
│       └── آبریزها
│
├── پیچ و رولپلاک (Screws & Wall Plugs)
│   ├── پیچ چوب (Wood Screws)
│   │   ├── پیچ چهارسو
│   │   ├── پیچ دوسو
│   │   └── پیچ سیدوس (آریا)
│   ├── رولپلاک (Wall Plugs)
│   │   ├── رولپلاک لبه دار
│   │   ├── رولپلاک شاخک دار
│   │   └── رولپلاک خاردار
│   └── پنج بوکسی (Box Nails)
│       └── پنج بوکسی نوک تیز
│
└── گلدان و آبپاش (Flower Pots & Watering Cans)
    ├── گلدان (Flower Pots)
    │   ├── گلدان استوانه‌ای
    │   ├── گلدان آجری
    │   ├── گلدان مهرآسا
    │   ├── گلدان دیواری
    │   ├── گلدان کاکتوسی
    │   └── گلدان نرده‌ای
    ├── زیرگلدانی (Pot Saucers)
    │   ├── زیرگلدانی مسی
    │   └── زیرگلدانی مربع
    └── آبپاش (Watering Cans)
        ├── آبپاش طرح گلبرگ
        └── محلول پاش
```

#### Command Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `--clear` | flag | Delete all existing categories before creation |

#### Behavior

- Creates superuser if none exists
- Uses `get_or_create` to avoid duplicates
- Generates slugs automatically
- Prints category tree after creation
- Returns success count

---

### 2. `seed_products` — Generate Mock Products

Creates realistic mock products distributed across existing categories.

#### Usage

```bash
# Create 200 products (default)
python manage.py seed_products

# Create 500 products
python manage.py seed_products --count=500

# Create products only in specific category
python manage.py seed_products --category="گلدان"

# Clear existing products first, then create 300
python manage.py seed_products --clear --count=300
```

#### Command Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--count` | int | `200` | Number of products to generate |
| `--clear` | flag | `False` | Delete existing products before creation |
| `--category` | str | `None` | Filter category by name (partial match) |

#### Product Generation Logic

##### Distribution Weights

| Category | Weight | Percentage |
|----------|--------|------------|
| گلدان و آبپاش | 35 | 35% |
| سایر دسته‌ها (each) | ~21.67 | ~65% total |

##### Category Depth Selection

| Depth | Probability |
|-------|-------------|
| Level 1 (main) | 40% |
| Level 2 (sub) | 35% |
| Level 3 (sub-sub) | 20% |
| Level 4 (sub-sub-sub) | 5% |

##### Pricing Strategy

| Status | Probability | Description |
|--------|-------------|-------------|
| Regular | ~55% | `price` between 50,000–5,000,000 Toman |
| On Sale | ~30% | `on_sale_price` = 70–90% of `price` |
| Call for Price | ~15% | `call_for_price=True`, `price=0` |

##### Product Flags

| Flag | Probability |
|------|-------------|
| `published` | 90% |
| `featured_in_special_sales` | 25% |
| `is_featured` | 15% |
| `featured_order` (1-100) | 15% (only if featured) |

##### Product Names

Names are generated based on category using real product data:

```python
names_map = {
    'پوست کن': ['پوست کن تیغه آلمانی', 'پوست کن طرح ترک', 'پوست کن معمولی'],
    'گلدان': ['گلدان استوانه‌ای', 'گلدان آجری', 'گلدان کاکتوسی'],
    'سردوش': ['سردوش گرد', 'سردوش مربعی', 'سردوش تلفنی'],
    # ...
}
```

Format: `{base_name} مدل {random_number_100-999}`

##### Descriptions

Generated with realistic Persian content:

```
{name} از جنس {material}. دارای {feature1} و {feature2}. مناسب {category}.
```

**Materials:** پلاستیک فشرده، استیل ضد زنگ، آلومینیوم، پلی‌اتیلن، ABS

**Features:** کیفیت بالا، طراحی ارگونومیک، دوام طولانی، نصب آسان، مناسب مصارف خانگی، بسته‌بندی استاندارد

##### Tags

Tags are generated hierarchically:
1. Current category name
2. All parent category names (walking up the tree)
3. 2 random tags from: کیفیت بالا، ارسال سریع، عمده فروشی، ضمانت، جدید

##### Images

Images are downloaded from [picsum.photos](https://picsum.photos):

```python
url = f'https://picsum.photos/800/600?random={random.randint(1, 1000)}'
```

- **Size:** 800×600 pixels
- **Format:** JPG
- **Saving:** `media/products/covers/product_{index}_{random}.jpg`
- **Fallback:** If download fails, product is created without image

---

### 3. `clear_mock_data` — Remove All Mock Data

Completely removes all mock data from the database.

#### Usage

```bash
# Delete all mock data
python manage.py clear_mock_data
```

#### What Gets Deleted

Deletion order (respects foreign key dependencies):

1. `ProductLike` — all likes
2. `ProductSave` — all saves
3. `ProductImage` — all product images
4. `Product` — all products
5. `Category` — all categories

#### Output

```
🗑️  در حال پاک کردن تمام محصولات و دسته‌بندی‌ها...
✅ {product_count} محصول و {category_count} دسته‌بندی پاک شد
```

---

## Complete Workflow

### Option 1: Fresh Start with Full Mock Data

```bash
# Step 1: Clear existing data
python manage.py clear_mock_data

# Step 2: Create category tree
python manage.py seed_categories

# Step 3: Generate 200 products
python manage.py seed_products --count=200
```

### Option 2: Single Command Pipeline

```bash
python manage.py seed_categories && python manage.py seed_products --count=200
```

### Option 3: Testing Specific Categories

```bash
# Only flower pots
python manage.py seed_products --category="گلدان" --count=50

# Only sanitary products
python manage.py seed_products --category="بهداشتی" --count=100
```

---

## Data Characteristics

### Total Generated Data (with defaults)

| Entity | Count |
|--------|-------|
| Main Categories | 4 |
| Sub-Categories | ~15 |
| Sub-Sub-Categories | ~40 |
| Sub-Sub-Sub-Categories | ~6 |
| **Total Categories** | **~65** |
| **Products** | **200** |

### Product Status Distribution (approximate)

| Status | Count (of 200) |
|--------|----------------|
| Regular | ~110 |
| On Sale | ~60 |
| Call for Price | ~30 |

### Category Distribution (of 200 products)

| Category | Products |
|----------|----------|
| گلدان و آبپاش | ~70 |
| محصولات آشپزخانه | ~43 |
| محصولات بهداشتی | ~43 |
| پیچ و رولپلاک | ~44 |

---

## Error Handling

### No Categories Exist

If you run `seed_products` before `seed_categories`:

```
❌ هیچ دسته‌بندی‌ای وجود ندارد!
ابتدا دستور زیر را اجرا کنید:
  python manage.py seed_categories
```

### Category Filter Not Found

```
❌ دسته‌بندی "فلان" یافت نشد
```

### Image Download Failure

- Product is still created
- No image is saved
- Process continues normally

### Missing Superuser

- If no superuser exists, one is created automatically:
  - Username: `admin`
  - Email: `admin@example.com`
  - Password: `admin123`

---

## Performance Considerations

| Aspect | Details |
|--------|---------|
| Image Download | 5-second timeout per image |
| Progress Logging | Every 25 products |
| Database Operations | Bulk-friendly (individual saves for flexibility) |
| Memory Usage | Streams images (doesn't keep all in memory) |

### Time Estimates

| Products | Estimated Time |
|----------|---------------|
| 50 | ~30 seconds |
| 200 | ~2-3 minutes |
| 500 | ~5-8 minutes |

*Time varies based on internet speed and picsum.photos availability.*

---

## Customization

### Changing Distribution Weights

In `seed_products.py`, modify the `weights` list:

```python
if 'گلدان' in cat.name:
    weights.append(35)  # Change this value
else:
    weights.append(65 / (len(main_categories) - 1))
```

### Changing Pricing Ranges

```python
price = random.randint(50000, 5000000)  # Min, Max in Toman
```

### Changing Sale Probability

```python
if random.random() < 0.30:  # Change 0.30 to desired percentage
    on_sale = int(price * random.uniform(0.7, 0.9))
```

### Changing Call-for-Price Probability

```python
if random.random() < 0.15:  # Change 0.15 to desired percentage
    return 0, None, True
```

---

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'faker'`

**Solution:**
```bash
pip install faker
```

### Issue: `ModuleNotFoundError: No module named 'requests'`

**Solution:**
```bash
pip install requests
```

### Issue: Products have no images

**Causes:**
- No internet connection
- picsum.photos is down
- Firewall blocking requests

**Solution:** Products will still be created; run the command again later or use a different image source.

### Issue: Slug conflicts

The system uses `get_or_create` and automatic slug generation handles duplicates.

### Issue: Command not found

**Solution:** Ensure `__init__.py` files exist:
```bash
touch apps/products/management/__init__.py
touch apps/products/management/commands/__init__.py
```

---

## Summary

| Command | Purpose | Key Flags |
|---------|---------|-----------|
| `seed_categories` | Create nested category tree | `--clear` |
| `seed_products` | Generate mock products | `--count`, `--clear`, `--category` |
| `clear_mock_data` | Remove all mock data | — |

This system provides a flexible, realistic, and comprehensive mock data generation solution for testing the Sidoos Plasco Shop Django application at scale.
```