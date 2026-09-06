"""
URL configuration for the blog's app.

Responsibility:
    Defines the `blogs` URL namespace: the Article Listing page (`/blogs/`)
    and the Article Detail page (`/blogs/<slug>/`).

    The detail route uses the `unicode_slug` converter (see
    apps/blogs/converters.py), not Django's built-in `<slug:...>`,
    since Article.slug supports Persian/Unicode text. It's registered
    below and must stay listed after the empty-path listing route so an
    empty path doesn't fall through to it.
"""

from django.urls import path, register_converter

from apps.blogs import views
from apps.blogs.converters import UnicodeSlugConverter

register_converter(UnicodeSlugConverter, "unicode_slug")

app_name = "blogs"

urlpatterns = [
    path("", views.article_list, name="article_list"),
    path("<unicode_slug:slug>/", views.article_detail, name="article_detail"),
]
