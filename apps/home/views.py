from django.shortcuts import render
from django.http import HttpResponse


def home(request):
    return render(request, 'home/index.html')


def robots_txt(request):
    """Serve crawler policy without exposing private application routes."""
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /accounts/",
        "Disallow: /support/",
        "Disallow: /sidoos-administration/",
        "Disallow: /ckeditor5/",
        "Disallow: /products/api/",
        "Sitemap: " + request.build_absolute_uri("/sitemap.xml"),
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")
