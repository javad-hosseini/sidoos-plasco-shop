from django.http import HttpResponse
from django.urls import reverse
from django.core.paginator import Page


def robots_txt(request):
    sitemap_url = request.build_absolute_uri(
        reverse("sitemap")
    )

    content = "\n".join([
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        "Disallow: /cart/",
        "Disallow: /checkout/",
        "Disallow: /support/",
        f"Sitemap: {sitemap_url}",
    ])

    return HttpResponse(content, content_type="text/plain")




#Pagination rel="prev" / rel="next" Headers
def add_pagination_headers(request, response, page_obj: Page):
    """
    Adds Link headers for prev/next pagination to a response.
    This tells Google that page 1, 2, 3... are part of a single series.
    """
    base_url = request.build_absolute_uri(request.path)
    query_params = request.GET.copy()
    links = []

    if page_obj.has_previous():
        query_params['page'] = page_obj.previous_page_number()
        # Remove empty query params if page=1 (clean URL)
        if query_params['page'] == 1:
            del query_params['page']
        full_url = base_url
        if query_params.urlencode():
            full_url = f"{base_url}?{query_params.urlencode()}"
        links.append(f'<{full_url}>; rel="prev"')

    if page_obj.has_next():
        query_params['page'] = page_obj.next_page_number()
        full_url = f"{base_url}?{query_params.urlencode()}"
        links.append(f'<{full_url}>; rel="next"')

    if links:
        # Multiple links can be comma-separated in one header
        response['Link'] = ', '.join(links)