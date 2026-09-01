from django.http import HttpResponse
from django.urls import reverse


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