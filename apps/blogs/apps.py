"""
Application configuration for the Sidoos blogs app.

This module defines the Django app configuration for the article
management system. It sets the app name and default auto field type.
"""

from django.apps import AppConfig


class BlogsConfig(AppConfig):
    """
    Configuration class for the blog's application.

    Defines the app name and the default auto field type for models
    in this application.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.blogs"
    verbose_name = "مقالات"