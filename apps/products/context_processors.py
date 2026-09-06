from .models import Category


def product_categories(request):
    """
    Expose the top-level category tree to every template (used by the
    navbar's category mega-menu).

    Children are prefetched a few levels deep so the recursive menu
    partial can render a nested tree without an N+1 explosion. Deeper
    branches still resolve correctly, just with extra queries.
    """
    return {
        'categories': (
            Category.objects
            .filter(parent__isnull=True)
            .prefetch_related('children__children__children')
            .order_by('name')
        )
    }
