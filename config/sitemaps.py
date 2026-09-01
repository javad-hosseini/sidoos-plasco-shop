from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.products.models import Category, Product


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return ["home:home", "products:product_list", "products:special_sales", "products:category_list", "blogs:article_list"]

    def location(self, item):
        return reverse(item)


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.filter(published=True).only("slug", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("products:product_detail", kwargs={"slug": obj.slug})


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Category.objects.all().only("slug")

    def location(self, obj):
        return reverse("products:category_products", kwargs={"slug": obj.slug})
