_PRIVATE_PREFIXES = (
    "/accounts/",
    "/support/",
    "/sidoos-administration/",
    "/ckeditor5/",
    "/products/api/",
)


def seo(request):
    """Provide one canonical URL policy for public HTML pages."""
    canonical_url = None
    if request.method == "GET" and not request.path.startswith(_PRIVATE_PREFIXES):
        canonical_url = request.build_absolute_uri(request.path)

    return {
        "canonical_url": canonical_url,
        "site_url": request.build_absolute_uri("/").rstrip("/"),
    }
