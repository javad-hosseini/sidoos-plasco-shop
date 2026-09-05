"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from config.sitemaps import StaticViewSitemap, ProductSitemap, CategorySitemap

from config import settings

sitemaps = {
    "static": StaticViewSitemap,
    "products": ProductSitemap,
    "categories": CategorySitemap,
}

# Note: robots.txt is served by apps.home.views.robots_txt, registered via
# the apps.home.urls include below (it lists the site's actual private
# paths - a separate project-level route here previously shadowed it with
# a stale list referencing routes that don't exist in this project).
urlpatterns = [
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('i18n/', include('django.conf.urls.i18n')),
    path('sidoos-administration/', admin.site.urls),
    path("ckeditor5/", include("django_ckeditor_5.urls")),

    path('', include('apps.home.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('blogs/', include('apps.blogs.urls')),
    path('products/', include('apps.products.urls')),
    path('support/', include('apps.support.urls')),

]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
