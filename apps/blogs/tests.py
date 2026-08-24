"""
Unit tests for the Sidoos blogs application models.

Tests cover:
- Article creation with required fields
- String representation
- Slug uniqueness and Unicode support
- Draft and published states
- Automatic timestamps
- Optional SEO fields
- Persian tag support
- Model validation
"""

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import Article


class ArticleModelTests(TestCase):
    """
    Test suite for the Article model.

    Verifies that articles can be created with Persian content,
    that slugs support Unicode characters, and that publication
    logic works correctly.
    """

    def setUp(self) -> None:
        """
        Creates base data for testing Article model behavior.
        """
        self.article_data = {
            "title": "راهنمای خرید گلدان پلاستیکی",
            "slug": "راهنمای-خرید-گلدان-پلاستیکی",
            "summary": "راهنمای کامل برای انتخاب و خرید گلدان پلاستیکی مناسب",
            "content": "<h2>مقدمه</h2><p>این یک مقاله آزمایشی است.</p>",
            "reading_time": 5,
        }

    def test_article_creation(self) -> None:
        """
        Tests that an Article can be created with valid data.
        """
        article = Article.objects.create(**self.article_data)

        self.assertEqual(article.title, "راهنمای خرید گلدان پلاستیکی")
        self.assertEqual(article.reading_time, 5)
        self.assertFalse(article.is_published)
        self.assertIsNotNone(article.created_at)
        self.assertIsNotNone(article.updated_at)

    def test_article_str_method(self) -> None:
        """
        Tests that __str__ returns the article title.
        """
        article = Article.objects.create(**self.article_data)
        self.assertEqual(str(article), "راهنمای خرید گلدان پلاستیکی")

    def test_slug_uniqueness(self) -> None:
        """
        Tests that slug must be unique across articles.
        """
        Article.objects.create(**self.article_data)

        # Attempt to create another article with the same slug
        with self.assertRaises(ValidationError):
            Article.objects.create(
                title="مقاله دیگری",
                slug="راهنمای-خرید-گلدان-پلاستیکی",  # Same slug
                summary="خلاصه مقاله",
                content="<p>محتوا</p>",
                reading_time=3,
            )

    def test_persian_unicode_slug_storage(self) -> None:
        """
        Tests that Persian/Unicode slugs are stored correctly without
        any ASCII normalization or encoding changes.
        """
        persian_slug = "بهترین-گلدان-برای-گیاهان-آپارتمانی"
        article = Article.objects.create(
            **{
                **self.article_data,
                "slug": persian_slug,
            }
        )

        # Retrieve from database to verify exact storage
        article_from_db = Article.objects.get(pk=article.pk)
        self.assertEqual(article_from_db.slug, persian_slug)
        self.assertEqual(article_from_db.slug, "بهترین-گلدان-برای-گیاهان-آپارتمانی")

    def test_mixed_unicode_slug(self) -> None:
        """
        Tests slugs containing both Persian and English characters.
        """
        mixed_slug = "buying-guide-گلدان-پلاستیکی-2024"
        article = Article.objects.create(
            **{
                **self.article_data,
                "slug": mixed_slug,
            }
        )
        self.assertEqual(article.slug, mixed_slug)

    def test_slug_with_spaces_gets_normalized(self) -> None:
        """
        Tests that spaces in slugs are automatically converted to hyphens.
        """
        slug_with_spaces = "راهنمای خرید گلدان پلاستیکی"
        article = Article.objects.create(
            **{
                **self.article_data,
                "slug": slug_with_spaces,
            }
        )

        self.assertEqual(article.slug, "راهنمای-خرید-گلدان-پلاستیکی")

    def test_draft_state_default(self) -> None:
        """
        Tests that articles are created as drafts by default.
        """
        article = Article.objects.create(**self.article_data)
        self.assertFalse(article.is_published)
        self.assertIsNone(article.published_at)

    def test_published_state(self) -> None:
        """
        Tests that articles can be published with a publication date.
        """
        published_at = timezone.now()
        article = Article.objects.create(
            **{
                **self.article_data,
                "is_published": True,
                "published_at": published_at,
            }
        )
        self.assertTrue(article.is_published)
        self.assertIsNotNone(article.published_at)
        self.assertEqual(article.published_at, published_at)

    def test_published_requires_date(self) -> None:
        """
        Tests that published articles require a publication date.
        """
        article = Article(
            **{
                **self.article_data,
                "is_published": True,
            }
        )
        with self.assertRaises(ValidationError):
            article.full_clean()

    def test_created_at_updated_at_auto_generated(self) -> None:
        """
        Tests that created_at and updated_at are automatically set.
        """
        article = Article.objects.create(**self.article_data)
        self.assertIsNotNone(article.created_at)
        self.assertIsNotNone(article.updated_at)

        # Verify created_at doesn't change on update
        original_created_at = article.created_at
        original_updated_at = article.updated_at

        # Wait a moment to ensure time difference
        import time
        time.sleep(1)

        article.title = "عنوان جدید"
        article.save()

        self.assertEqual(article.created_at, original_created_at)
        self.assertGreater(article.updated_at, original_updated_at)

    def test_optional_seo_fields(self) -> None:
        """
        Tests that SEO fields are optional and can be left empty.
        """
        article = Article.objects.create(**self.article_data)

        self.assertEqual(article.meta_title, "")
        self.assertEqual(article.meta_description, "")
        self.assertEqual(article.canonical_url, "")
        self.assertEqual(article.og_title, "")
        self.assertEqual(article.og_description, "")
        self.assertEqual(article.robots, "index,follow")

    def test_persian_tags_support(self) -> None:
        """
        Tests that Persian/Unicode tags can be added to articles.
        """
        article = Article.objects.create(**self.article_data)
        article.tags.add("گلدان", "باغبانی", "خرید گلدان")

        self.assertEqual(article.tags.count(), 3)

        tag_names = [tag.name for tag in article.tags.all()]
        self.assertIn("گلدان", tag_names)
        self.assertIn("باغبانی", tag_names)
        self.assertIn("خرید گلدان", tag_names)

    def test_slug_validation_rejects_invalid_chars(self) -> None:
        """
        Tests that slug validation rejects invalid characters.
        """
        article = Article(
            **{
                **self.article_data,
                "slug": "invalid@slug#",
            }
        )
        with self.assertRaises(ValidationError):
            article.full_clean()

    def test_reading_time_validation(self) -> None:
        """
        Tests that reading time must be a positive integer between 1 and 60.
        """
        article = Article(
            **{
                **self.article_data,
                "reading_time": 0,
            }
        )
        with self.assertRaises(ValidationError):
            article.full_clean()

        article = Article(
            **{
                **self.article_data,
                "reading_time": 61,
            }
        )
        with self.assertRaises(ValidationError):
            article.full_clean()