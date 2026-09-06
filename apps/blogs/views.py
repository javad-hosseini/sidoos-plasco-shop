"""
Views for the blogs app.

Responsibility:
    The Article Listing page ("/blogs/") and the Article Detail page
    ("/blogs/<slug>/").

Architectural decisions:
    - Function-based views: each is a single, simple read-only query
      (+ pagination for the list), which doesn't benefit from the extra
      structure of class-based Views for this project's conventions.
    - `prefetch_related('tags')` is used (not `select_related`) because
      `tags` is a django-taggit ManyToMany-style relation; without it,
      rendering each card's tags would issue one extra query per article
      (classic N+1). A single prefetch query covers the whole page.
    - Only published articles are ever queried (`is_published=True`);
      drafts are never exposed on either view.
"""

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.http import http_date

from apps.blogs.models import Article
from config.seo import add_pagination_headers

# Number of articles per page. 12 divides evenly into the 3-column
# desktop / 2-column tablet / 1-column mobile grid described in the
# design spec (12 = 4 rows of 3, 6 rows of 2, 12 rows of 1).
ARTICLES_PER_PAGE = 12

# How many other articles to suggest at the bottom of an article's page.
RELATED_ARTICLES_LIMIT = 3


def _magazine_breadcrumbs():
    """Home / Magazine, as a base for every blogs-app breadcrumb trail."""
    return [
        {"label": "خانه", "url": reverse("home:home")},
        {"label": "مجله سیدوس", "url": reverse("blogs:article_list")},
    ]


def article_list(request):
    """
    Render the Sidoos Magazine article listing page.

    Displays only published articles, newest first, paginated.
    """
    published_articles = (
        Article.objects.filter(is_published=True)
        .order_by("-published_at")
        .prefetch_related("tags")
    )

    paginator = Paginator(published_articles, ARTICLES_PER_PAGE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    breadcrumbs = _magazine_breadcrumbs()
    breadcrumbs[-1]["url"] = None  # current page

    context = {
        "page_obj": page_obj,
        "articles": page_obj.object_list,
        "breadcrumbs": breadcrumbs,
    }
    response = render(request, 'blogs/article_list.html', context)# adds pagination (rel="prev" / rel="next") headers to response
    # Tell Google not to index any page beyond page 1
    if page_obj.number > 1:
        response['X-Robots-Tag'] = 'noindex, follow'

    add_pagination_headers(request, response, page_obj)
    return response


def article_detail(request, slug):
    """Render a single published article, with a few other articles to read next."""
    article = get_object_or_404(Article, slug=slug, is_published=True)

    related_articles = (
        Article.objects.filter(is_published=True)
        .exclude(pk=article.pk)
        .order_by("-published_at")
        .prefetch_related("tags")[:RELATED_ARTICLES_LIMIT]
    )

    breadcrumbs = _magazine_breadcrumbs()
    breadcrumbs.append({"label": article.title, "url": None})

    context = {
        "article": article,
        "related_articles": related_articles,
        "breadcrumbs": breadcrumbs,
    }

    #get absolute canonical URL
    canonical = article.canonical_url or request.build_absolute_uri(
        reverse('blogs:article_detail', kwargs={'slug': article.slug})
    )

    response = render(request, "blogs/article_detail.html", context)
    # adding Last-Modified timestamp for SEO/Crawler optimization
    response['Last-Modified'] = http_date(article.updated_at.timestamp())
    # adding canonical URL to the header response
    response['Link'] = f'<{canonical}>; rel="canonical"'
    #cache response in CDN and Browsers for 10 minutes
    response['Cache-Control'] = 'public, max-age=600'
    return response
