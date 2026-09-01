from django.urls.converters import StringConverter


class UnicodeSlugConverter(StringConverter):
    regex = "[^/]+"
