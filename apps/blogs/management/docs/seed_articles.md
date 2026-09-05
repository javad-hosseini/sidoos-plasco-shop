# Blog Mock Data Commands

Two Django management commands for generating and clearing mock `Article` data (`apps/blogs`), for local testing of the blog/magazine section.

```
apps/blogs/management/
├── __init__.py
└── commands/
    ├── __init__.py
    ├── seed_articles.py
    └── clear_mock_articles.py
```

## Prerequisites

```bash
pip install faker
```

Pillow (`PIL`) is also required for the placeholder cover images; it's already a project dependency.

---

## `seed_articles`

Generates mock `Article` rows: title, slug, summary, HTML content, reading time, publish state, a placeholder cover image, and tags.

```bash
python manage.py seed_articles
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--count` | int | `50` | Number of articles to create |
| `--clear` | flag | `False` | Delete all existing articles before generating new ones |

### Examples

```bash
# Default: create 50 articles
python manage.py seed_articles

# Create a specific number
python manage.py seed_articles --count=150

# Wipe existing articles first, then create 50 fresh ones
python manage.py seed_articles --clear

# Combine both
python manage.py seed_articles --clear --count=200
```

Running the command again **without** `--clear` adds more articles on top of what's already there — it never touches or duplicates existing rows.

### How it works

**Titles.** Built from a prefix × topic grid (`TITLE_PREFIXES` × `TITLE_TOPICS` in the command file), e.g. *"راهنمای خرید سیفون آشپزخانه و حمام"*, so they read like real headlines instead of random word salad. The grid currently has 10 × 12 = 120 combinations. If `--count` exceeds the number of remaining unique combinations, the command falls back to appending a unique numeric suffix (via `faker`'s `.unique` sequence) so titles never run out or collide.

**Uniqueness.** `Article.title` has no DB-level uniqueness constraint, but `Article.slug` does, and `Article.save()` calls `full_clean()`, which validates uniqueness before every save. The command preloads every existing title/slug from the database at start-up and checks new ones against that set, so it's always safe to run — whether it's the first run or the fifty-first, and regardless of `--count`.

**Slugs.** `Article` stores its slug as a `CharField` (not Django's ASCII-only `SlugField`) so it can hold Persian text, and `Article.clean()` validates it against a specific allowed character set (Persian letters, `\w`, spaces, hyphens). The command mirrors that exact character set when deriving a slug from the title, so a generated slug can never fail validation — even if a title contains a character outside that set (e.g. a zero-width non-joiner), it gets stripped before the slug is built.

**Content.** Each article gets 2–4 random section headings (`<h2>`) drawn from a fixed pool, each followed by 1–2 Persian paragraphs, plus a closing "جمع‌بندی" (Summary) section. Paragraph text comes from `Faker('fa_IR')` — real Persian words, though not grammatically meaningful ("lorem ipsum"-style filler). The multi-heading structure exists because the front end parses `<h2>` tags from article content to build a table of contents.

**Reading time.** A plain random integer between 2 and 15 minutes. (An earlier version tried to derive this from word count, but the short Faker paragraphs always rounded down to 1 minute regardless of content — a random value in a realistic range is more honest mock data than fake precision.)

**Publish state.** Each article randomly lands in one of three states, matching the three states the admin's `PublishedFilter` already recognizes:

| State | Probability | `is_published` | `published_at` |
|-------|------------|-----------------|-----------------|
| Draft | 20% | `False` | `None` |
| Scheduled | 10% | `True` | 1–30 days in the future |
| Published | 70% | `True` | random time in the last ~18 months |

**Cover image.** A 1200×675 placeholder image generated locally with Pillow (solid background + border + the article title rendered as text) — no network calls. The Persian font used to render the title text is resolved from disk once per command run and reused for every image, rather than re-searched on every single article.

**Tags.** 2–4 random tags sampled from a fixed pool of blog-relevant topics (`آشپزخانه`, `دکوراسیون`, `باغبانی`, etc.), added via the article's `TaggableManager`.

**SEO fields.** `meta_title`/`og_title` are set to the article title, and `meta_description`/`og_description` to the generated summary, so SEO-related templates/admin views have realistic data to render too.

---

## `clear_mock_articles`

Deletes **every** `Article` row in the database.

```bash
python manage.py clear_mock_articles
```

No flags. `Article` has no related models of its own (no per-article images/likes/etc. tables like the products app has), so deleting `Article` rows is all that's needed — no cascading cleanup step required.

This does not delete the actual image files that were uploaded to `MEDIA_ROOT` for those articles' cover images — only the database rows.

---

## One-liner: fresh start

```bash
python manage.py clear_mock_articles && python manage.py seed_articles --count=50
```

---

# Cheat Sheet

```bash
# Create 50 articles (default)
python manage.py seed_articles

# Create a specific number
python manage.py seed_articles --count=150

# Wipe existing articles, then create 50
python manage.py seed_articles --clear

# Wipe and create a specific number
python manage.py seed_articles --clear --count=200

# Delete ALL articles
python manage.py clear_mock_articles

# Fresh start in one line
python manage.py clear_mock_articles && python manage.py seed_articles --count=50
```

| Command | Flag | Type | Default | Description |
|---------|------|------|---------|-------------|
| `seed_articles` | `--count` | int | `50` | Number of articles to create |
| `seed_articles` | `--clear` | flag | `False` | Delete existing articles first |
| `clear_mock_articles` | *(none)* | — | — | Deletes every article |

| Publish state | Probability |
|----------------|-------------|
| Draft | 20% |
| Scheduled (future `published_at`) | 10% |
| Published (past `published_at`) | 70% |

| Field | Source |
|-------|--------|
| Title | Curated prefix × topic grid (Persian), unique-suffix fallback beyond 120 combos |
| Slug | Derived from title, filtered to `Article.clean()`'s allowed charset |
| Content | `Faker('fa_IR')` paragraphs under 2–4 random `<h2>` section headings |
| Reading time | Random int, 2–15 |
| Cover image | 1200×675 Pillow placeholder, generated locally (no network) |
| Tags | 2–4 random tags from a fixed Persian pool |

**Requires:** `pip install faker` (Pillow already a project dependency).
