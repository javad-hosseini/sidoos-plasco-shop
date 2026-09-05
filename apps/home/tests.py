from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.blogs.models import Article
from apps.home.models import HeroSlide
from apps.products.models import Category, Product


def _image():
    return SimpleUploadedFile(
        name="t.gif",
        content=(
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00"
            b"\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00"
            b"\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        ),
        content_type="image/gif",
    )


class HomePageTests(TestCase):
    def test_home_renders_with_no_content(self):
        response = self.client.get(reverse("home:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/index.html")

    def test_home_renders_with_content(self):
        user = get_user_model().objects.create_user(username="staff", password="x")
        category = Category.objects.create(name="گلدان", creator=user)
        Product.objects.create(
            name="گلدان نمونه",
            description="x",
            price=10000,
            cover_image=_image(),
            published=True,
            is_featured=True,
            featured_order=1,
            category=category,
            creator=user,
        )
        Product.objects.create(
            name="گلدان فروش ویژه",
            description="x",
            price=20000,
            on_sale_price=15000,
            cover_image=_image(),
            published=True,
            featured_in_special_sales=True,
            creator=user,
        )
        HeroSlide.objects.create(
            title="خط اول\nخط دوم",
            eyebrow="پیش‌عنوان",
            subtitle="توضیح",
            cta_label="فروشگاه",
            cta_url_name="products:product_list",
            background_image="home/hero/x.jpg",
        )
        Article.objects.create(
            title="مقاله نمونه",
            slug="مقاله-نمونه",
            summary="خلاصه",
            content="محتوا",
            reading_time=4,
            is_published=True,
            published_at=timezone.now(),
        )

        response = self.client.get(reverse("home:home"))
        self.assertEqual(response.status_code, 200)
        # "گلدان نمونه" (is_featured=True) is queried into featured_products,
        # but that section's UI was superseded by the admin-curated
        # BestSeller section (see HomeSectionFilteringTests) and is no
        # longer rendered in home/index.html - so we assert on the
        # queryset the view builds, not on page HTML that was never meant
        # to include it anymore.
        featured_names = [p.name for p in response.context["featured_products"]]
        self.assertIn("گلدان نمونه", featured_names)
        self.assertContains(response, "فروش ویژه سیدوس")
        self.assertContains(response, "مقاله نمونه")

    def test_hero_slide_cta_url_resolves(self):
        slide = HeroSlide(cta_url_name="products:special_sales")
        self.assertEqual(slide.get_cta_url(), reverse("products:special_sales"))

    def test_hero_slide_cta_url_blank(self):
        self.assertEqual(HeroSlide(cta_url_name="").get_cta_url(), "")

    def test_robots_txt_disallows_private_paths(self):
        response = self.client.get(reverse("home:robots_txt"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        body = response.content.decode()
        self.assertIn("Disallow: /accounts/", body)
        self.assertIn("Disallow: /sidoos-administration/", body)
        self.assertIn("Sitemap:", body)


class HomeSectionFilteringTests(TestCase):
    """
    Verifies the home view only surfaces admin-curated, active, published
    entries in each section — not just that the section renders.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="creator", password="x")
        self.category = Category.objects.create(name="گلدان", creator=self.user)

    def _product(self, **kwargs):
        defaults = dict(
            description="x",
            price=10000,
            cover_image=_image(),
            published=True,
            creator=self.user,
            category=self.category,
        )
        defaults.update(kwargs)
        return Product.objects.create(**defaults)

    def test_inactive_best_seller_is_hidden(self):
        from apps.home.models import BestSeller

        visible = self._product(name="پرفروش فعال")
        hidden_product = self._product(name="پرفروش غیرفعال")
        BestSeller.objects.create(product=visible, is_active=True, display_order=1)
        BestSeller.objects.create(product=hidden_product, is_active=False, display_order=2)

        response = self.client.get(reverse("home:home"))
        self.assertContains(response, "پرفروش فعال")
        self.assertNotContains(response, "پرفروش غیرفعال")

    def test_unpublished_best_seller_product_is_hidden(self):
        from apps.home.models import BestSeller

        unpublished = self._product(name="پرفروش منتشرنشده", published=False)
        # BestSeller.clean() would reject this combination, but clean() is
        # only enforced by full_clean()/ModelForms, not by plain .save() -
        # so this row can exist, and the *view* must filter it out too
        # (defense in depth via product__published=True in the query).
        entry = BestSeller(product=unpublished, is_active=True)
        entry.save()
        response = self.client.get(reverse("home:home"))
        self.assertNotContains(response, "پرفروش منتشرنشده")

    def test_inactive_featured_category_is_hidden(self):
        from apps.home.models import FeaturedCategory

        FeaturedCategory.objects.create(
            category=self.category, image=_image(), is_active=False,
        )
        response = self.client.get(reverse("home:home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.category, [fc.category for fc in response.context["featured_categories"]])

    def test_special_offer_requires_flag_active_and_published(self):
        from apps.home.models import SpecialSaleFeature

        flagged_and_visible = self._product(
            name="ویژه نمایان", featured_in_special_sales=True,
        )
        SpecialSaleFeature.objects.create(product=flagged_and_visible, is_active=True)

        response = self.client.get(reverse("home:home"))
        self.assertContains(response, "ویژه نمایان")


class BestSellerModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="u", password="x")
        self.category = Category.objects.create(name="دسته", creator=self.user)

    def test_str_includes_status(self):
        from apps.home.models import BestSeller

        product = Product.objects.create(
            name="محصول", description="x", price=1000, cover_image=_image(),
            published=True, creator=self.user,
        )
        entry = BestSeller.objects.create(product=product, is_active=True)
        self.assertIn("فعال", str(entry))
        self.assertIn(product.name, str(entry))

    def test_active_entry_for_unpublished_product_is_rejected(self):
        from apps.home.models import BestSeller

        product = Product.objects.create(
            name="پیش‌نویس", description="x", price=1000, cover_image=_image(),
            published=False, creator=self.user,
        )
        entry = BestSeller(product=product, is_active=True)
        with self.assertRaises(ValidationError):
            entry.full_clean()

    def test_inactive_entry_for_unpublished_product_is_allowed(self):
        from apps.home.models import BestSeller

        product = Product.objects.create(
            name="پیش‌نویس ۲", description="x", price=1000, cover_image=_image(),
            published=False, creator=self.user,
        )
        entry = BestSeller(product=product, is_active=False)
        entry.full_clean()  # should not raise

    def test_product_can_only_be_a_best_seller_once(self):
        from apps.home.models import BestSeller

        product = Product.objects.create(
            name="یکتا", description="x", price=1000, cover_image=_image(),
            published=True, creator=self.user,
        )
        BestSeller.objects.create(product=product)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                BestSeller.objects.create(product=product)


class FeaturedCategoryModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="u2", password="x")
        self.category = Category.objects.create(name="دسته دو", creator=self.user)

    def test_str_includes_status(self):
        from apps.home.models import FeaturedCategory

        entry = FeaturedCategory.objects.create(category=self.category, image=_image(), is_active=True)
        self.assertIn("فعال", str(entry))
        self.assertIn(self.category.name, str(entry))

    def test_category_can_only_be_featured_once(self):
        from apps.home.models import FeaturedCategory

        FeaturedCategory.objects.create(category=self.category, image=_image())
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FeaturedCategory.objects.create(category=self.category, image=_image())


class SpecialSaleFeatureModelTests(TestCase):
    """Covers the core business rule: only flagged products are selectable."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="u3", password="x")

    def _product(self, flagged):
        return Product.objects.create(
            name="محصول فروش ویژه" if flagged else "محصول عادی",
            description="x", price=1000, cover_image=_image(),
            published=True, creator=self.user,
            featured_in_special_sales=flagged,
        )

    def test_flagged_product_is_accepted(self):
        from apps.home.models import SpecialSaleFeature

        product = self._product(flagged=True)
        entry = SpecialSaleFeature.objects.create(product=product)
        self.assertTrue(entry.pk)

    def test_unflagged_product_is_rejected(self):
        from apps.home.models import SpecialSaleFeature

        product = self._product(flagged=False)
        with self.assertRaises(ValidationError):
            SpecialSaleFeature.objects.create(product=product)

    def test_unflagged_product_rejected_even_via_full_clean_directly(self):
        from apps.home.models import SpecialSaleFeature

        product = self._product(flagged=False)
        entry = SpecialSaleFeature(product=product)
        with self.assertRaises(ValidationError):
            entry.full_clean()


class NewsletterSubscribeViewTests(TestCase):
    def setUp(self):
        self.url = reverse("home:newsletter_subscribe")

    def test_valid_email_is_saved(self):
        from apps.home.models import NewsletterSubscriber

        response = self.client.post(self.url, {"email": "Visitor@Example.com"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(
            NewsletterSubscriber.objects.filter(email="visitor@example.com").exists()
        )

    def test_duplicate_email_is_not_created_twice(self):
        from apps.home.models import NewsletterSubscriber

        NewsletterSubscriber.objects.create(email="dup@example.com")
        response = self.client.post(self.url, {"email": "dup@example.com"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertTrue(data.get("already_subscribed"))
        self.assertEqual(NewsletterSubscriber.objects.filter(email="dup@example.com").count(), 1)

    def test_invalid_email_is_rejected(self):
        response = self.client.post(self.url, {"email": "not-an-email"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_empty_email_is_rejected(self):
        response = self.client.post(self.url, {"email": ""})
        self.assertEqual(response.status_code, 400)

    def test_missing_email_field_is_rejected(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 400)

    def test_get_method_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_csrf_is_enforced(self):
        from django.test import Client

        enforcing_client = Client(enforce_csrf_checks=True)
        response = enforcing_client.post(self.url, {"email": "csrf-check@example.com"})
        self.assertEqual(response.status_code, 403)
