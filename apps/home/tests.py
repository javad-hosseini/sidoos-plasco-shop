from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
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
        self.assertContains(response, "گلدان نمونه")
        self.assertContains(response, "فروش ویژه سیدوس")
        self.assertContains(response, "مقاله نمونه")

    def test_hero_slide_cta_url_resolves(self):
        slide = HeroSlide(cta_url_name="products:special_sales")
        self.assertEqual(slide.get_cta_url(), reverse("products:special_sales"))

    def test_hero_slide_cta_url_blank(self):
        self.assertEqual(HeroSlide(cta_url_name="").get_cta_url(), "")
