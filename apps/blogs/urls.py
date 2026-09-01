"""
URL configuration for the blog's app.

Responsibility:
    Defines the `blogs` URL namespace. Currently only registers the
    Article Listing page (`/blogs/`).

Architectural decision — Article Detail route intentionally omitted:
    The Article Detail view/template is out of scope for this task, and
    the task instructions explicitly forbid inventing a fake URL
    implementation for it. So `blogs:article_detail` is NOT registered
    here yet.

    The listing template references it via:
        {% url 'blogs:article_detail' article.slug as article_url %}
    which is Django's "safe" form of the {% url %} tag — if the name
    doesn't resolve (as is currently the case), `article_url` is simply
    left unset instead of raising NoReverseMatch, so the listing page
    keeps working today.

    When the Article Detail page is implemented, add a route here such as:

        from apps.blogs.converters import UnicodeSlugConverter
        from django.urls import register_converter
        register_converter(UnicodeSlugConverter, "unicode_slug")

        path(
            "<unicode_slug:slug>/",
            views.article_detail,
            name="article_detail",
        ),

    The `unicode_slug` converter (see apps/blogs/converters.py) is
    registered below already so it's ready to use as soon as that view
    exists — it must NOT use Django's built-in `<slug:...>` converter,
    since Article.slug supports Persian/Unicode text.
"""

from django.urls import path, register_converter

from apps.blogs import views
from apps.blogs.converters import UnicodeSlugConverter

register_converter(UnicodeSlugConverter, "unicode_slug")

app_name = "blogs"

urlpatterns = [
    path("", views.article_list, name="article_list"),
]
