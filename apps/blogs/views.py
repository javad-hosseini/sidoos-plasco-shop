"""
Views for the blogs app.

Responsibility:
    Currently implements only the Article Listing page ("/blogs/").
    The Article Detail view is intentionally NOT implemented here yet
    (see project task scope) — the listing page links to
    `blogs:article_detail`, a URL name that does not exist until that
    view is built.

Architectural decisions:
    - Function-based view: the listing page is a single, simple read-only
      query + pagination, which doesn't benefit from the extra structure
      of a class-based ListView for this project's conventions.
    - `prefetch_related('tags')` is used (not `select_related`) because
      `tags` is a django-taggit ManyToMany-style relation; without it,
      rendering each card's tags would issue one extra query per article
      (classic N+1). A single prefetch query covers the whole page.
    - Only published articles are ever queried (`is_published=True`);
      drafts are never exposed on this view.
"""

from django.core.paginator import Paginator
from django.shortcuts import render

from apps.blogs.models import Article

# Number of articles per page. 12 divides evenly into the 3-column
# desktop / 2-column tablet / 1-column mobile grid described in the
# design spec (12 = 4 rows of 3, 6 rows of 2, 12 rows of 1).
ARTICLES_PER_PAGE = 12


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

    context = {
        "page_obj": page_obj,
        "articles": page_obj.object_list,
    }
    return render(request, "blogs/article_list.html", context)
