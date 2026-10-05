from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse, HttpResponseNotFound
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.blogs.models import Article
from apps.products.models import Category, Product
from utils.middleware import LegacyRedirectMiddleware


class LegacyRedirectMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            phone_number='09123456789',
            first_name='Test',
            last_name='User'
        )
        self.category = Category.objects.create(
            name='Kitchen',
            slug='kitchen-tools',
            creator=self.user
        )
        dummy_img = SimpleUploadedFile(
            name='test_cover.jpg',
            content=b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9',
            content_type='image/jpeg'
        )
        self.product = Product.objects.create(
            name='Test Bucket',
            slug='test-bucket',
            description='<p>Test description</p>',
            price=100000,
            cover_image=dummy_img,
            category=self.category,
            creator=self.user,
            published=True
        )
        self.article = Article.objects.create(
            title='Test Article',
            slug='test-article',
            summary='Summary',
            content='<p>Content</p>',
            reading_time=3,
            is_published=True,
            published_at=timezone.now(),
        )

    def test_product_redirect(self):
        middleware = LegacyRedirectMiddleware(lambda r: HttpResponse("OK"))
        request = self.factory.get('/product/test-bucket/')
        response = middleware(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/products/test-bucket/')

    def test_persian_product_redirect(self):
        middleware = LegacyRedirectMiddleware(lambda r: HttpResponse("OK"))
        # Percent-encoded Persian slug
        request = self.factory.get('/product/%D8%B3%D8%B1%D9%88%DB%8C%D8%B3-%D9%BE%D9%84%D8%A7%D8%B3%DA%A9%D9%88/')
        response = middleware(request)
        self.assertEqual(response.status_code, 301)
        self.assertIn('/products/', response['Location'])

    def test_category_redirect(self):
        middleware = LegacyRedirectMiddleware(lambda r: HttpResponse("OK"))
        request = self.factory.get('/product-category/kitchen-tools/')
        response = middleware(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/products/categories/kitchen-tools/')

    def test_mag_article_redirect(self):
        middleware = LegacyRedirectMiddleware(lambda r: HttpResponse("OK"))
        request = self.factory.get('/mag/test-article/')
        response = middleware(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/blogs/test-article/')

    def test_blog_article_redirect(self):
        middleware = LegacyRedirectMiddleware(lambda r: HttpResponse("OK"))
        request = self.factory.get('/blog/test-article/')
        response = middleware(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/blogs/test-article/')

    def test_query_param_redirect(self):
        middleware = LegacyRedirectMiddleware(lambda r: HttpResponse("OK"))
        request = self.factory.get(f'/?p={self.product.pk}')
        response = middleware(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], f'/products/{self.product.slug}/')

    def test_query_param_category_redirect(self):
        middleware = LegacyRedirectMiddleware(lambda r: HttpResponse("OK"))
        request = self.factory.get('/?product_cat=kitchen-tools')
        response = middleware(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/products/categories/kitchen-tools/')

    def test_fallback_404_product_match(self):
        middleware = LegacyRedirectMiddleware(lambda r: HttpResponseNotFound("Not Found"))
        request = self.factory.get('/test-bucket/')
        response = middleware(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/products/test-bucket/')

    def test_fallback_404_article_match(self):
        middleware = LegacyRedirectMiddleware(lambda r: HttpResponseNotFound("Not Found"))
        request = self.factory.get('/test-article/')
        response = middleware(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/blogs/test-article/')

    def test_normal_route_pass_through(self):
        middleware = LegacyRedirectMiddleware(lambda r: HttpResponse("Normal Route OK"))
        request = self.factory.get('/products/')
        response = middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Normal Route OK")

    def test_seo_search_robots_header(self):
        response = self.client.get('/products/?q=bucket')
        self.assertEqual(response['X-Robots-Tag'], 'noindex, follow')
        self.assertContains(response, '<meta name="robots" content="noindex, follow">')

    def test_seo_homepage_structured_data(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SearchAction')
        self.assertContains(response, 'Organization')
        self.assertContains(response, 'WebSite')

    def test_seo_faq_structured_data(self):
        response = self.client.get('/faq/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'FAQPage')

    def test_seo_breadcrumbs_structured_data(self):
        response = self.client.get(f'/products/{self.product.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'BreadcrumbList')
        self.assertContains(response, 'Product')


class AdminInternalLinkSearchTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='adminuser',
            phone_number='09121111111',
            first_name='Admin',
            last_name='User',
            password='adminpassword'
        )
        self.regular_user = User.objects.create_user(
            username='reguser',
            phone_number='09122222222',
            first_name='Regular',
            last_name='User',
            password='regpassword'
        )
        self.category = Category.objects.create(
            name='گلدان پلاستیکی',
            slug='plastic-pots',
            creator=self.admin_user
        )
        dummy_img = SimpleUploadedFile(
            name='test_pot.jpg',
            content=b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9',
            content_type='image/jpeg'
        )
        self.product = Product.objects.create(
            name='گلدان مدل آکاردئونی',
            slug='accordion-pot',
            description='<p>توضیحات تست</p>',
            price=75000,
            cover_image=dummy_img,
            category=self.category,
            creator=self.admin_user,
            published=True
        )
        self.article = Article.objects.create(
            title='راهنمای انتخاب گلدان مناسب',
            slug='pot-buying-guide',
            summary='خلاصه مقاله',
            content='<p>محتوای مقاله</p>',
            reading_time=4,
            is_published=True,
            published_at=timezone.now(),
        )

    def test_anonymous_user_redirected(self):
        response = self.client.get('/sidoos-administration/internal-link-search/?q=گلدان')
        # staff_member_required redirects non-staff/anonymous to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/sidoos-administration/login/', response['Location'])

    def test_regular_non_staff_user_redirected(self):
        self.client.force_login(self.regular_user)
        response = self.client.get('/sidoos-administration/internal-link-search/?q=گلدان')
        self.assertEqual(response.status_code, 302)

    def test_staff_search_all(self):
        self.client.force_login(self.admin_user)
        response = self.client.get('/sidoos-administration/internal-link-search/?q=گلدان')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        titles = [r['title'] for r in data['results']]
        self.assertIn('گلدان مدل آکاردئونی', titles)
        self.assertIn('راهنمای انتخاب گلدان مناسب', titles)
        self.assertIn('گلدان پلاستیکی', titles)

        # Verify URL structures
        urls = [r['url'] for r in data['results']]
        self.assertIn('/products/accordion-pot/', urls)
        self.assertIn('/blogs/pot-buying-guide/', urls)
        self.assertIn('/products/categories/plastic-pots/', urls)

    def test_staff_search_product_type_filter(self):
        self.client.force_login(self.admin_user)
        response = self.client.get('/sidoos-administration/internal-link-search/?q=گلدان&type=product')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        types = {r['type'] for r in data['results']}
        self.assertEqual(types, {'product'})
        self.assertEqual(data['results'][0]['title'], 'گلدان مدل آکاردئونی')

    def test_staff_search_article_type_filter(self):
        self.client.force_login(self.admin_user)
        response = self.client.get('/sidoos-administration/internal-link-search/?q=گلدان&type=article')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        types = {r['type'] for r in data['results']}
        self.assertEqual(types, {'article'})
        self.assertEqual(data['results'][0]['title'], 'راهنمای انتخاب گلدان مناسب')

    def test_staff_empty_query_returns_recent_items(self):
        self.client.force_login(self.admin_user)
        response = self.client.get('/sidoos-administration/internal-link-search/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data['results']), 0)


