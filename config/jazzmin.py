"""
Jazzmin Configuration
Reusable for all Django projects.
"""

# ==========================================================
# JAZZMIN SETTINGS
# ==========================================================

JAZZMIN_SETTINGS = {

    # ------------------------------------------------------
    # Branding
    # ------------------------------------------------------

    "site_title": "پنل مدیریت سیدوس",
    "site_header": "مدیریت سیدوس",
    "site_brand": "سیدوس",

    "site_logo": "images/logo.png",
    "site_icon": "images/favicon.ico",

    "login_logo": "images/logo.png",
    "login_logo_dark": None,

    "site_logo_classes": "img-circle elevation-2",

    "welcome_sign": "به پنل مدیریت سیدوس خوش آمدید",

    # "copyright": "© 2026",

    # ------------------------------------------------------
    # Theme
    # ------------------------------------------------------

    "show_theme_chooser": True,

    "default_theme_mode": "auto",

    # ------------------------------------------------------
    # Navigation
    # ------------------------------------------------------

    "show_sidebar": True,

    "navigation_expanded": False,

    "hide_apps": [],

    "hide_models": [],

    "order_with_respect_to": [
        "auth",
    ],

    # ------------------------------------------------------
    # Search
    # ------------------------------------------------------

    "search_model": [
        "accounts.User",
    ],

    # ------------------------------------------------------
    # User Menu
    # ------------------------------------------------------

    # "usermenu_links": [
    #
    #     {
    #         "name": "GitHub",
    #         "url": "https://github.com",
    #         "new_window": True,
    #     },
    #
    # ],

    # ------------------------------------------------------
    # Top Menu
    # ------------------------------------------------------

    "topmenu_links": [

        {
            "name": "داشبورد",
            "url": "admin:index",
        },

    ],

    # ------------------------------------------------------
    # Icons
    # ------------------------------------------------------

    "icons": {

        # Django Apps

        "auth": "fas fa-users",
        "accounts": "fas fa-users",

        # Django Models

        "accounts.user": "fas fa-user",

        "auth.group": "fas fa-users-cog",

    },

    "default_icon_parents": "fas fa-folder",

    "default_icon_children": "fas fa-circle",

    # ------------------------------------------------------
    # Forms
    # ------------------------------------------------------

    "related_modal_active": True,

    "changeform_format": "horizontal_tabs",

    "changeform_format_overrides": {

        "auth.user": "collapsible",

    },

    # ------------------------------------------------------
    # Language
    # ------------------------------------------------------

    "language_chooser": True,

    # ------------------------------------------------------
    # Custom assets
    # ------------------------------------------------------

    # RTL polish for admins who switch the language to Persian, via the
    # language chooser above. Scoped to html[dir="rtl"], so it has no
    # effect while the interface is in English.
    "custom_css": "admin/css/rtl-polish.css",

}

# ==========================================================
# UI
# ==========================================================

JAZZMIN_UI_TWEAKS = {

    # ------------------------------------------------------
    # Theme
    # ------------------------------------------------------

    "theme": "flatly",

    # ------------------------------------------------------
    # Navbar
    # ------------------------------------------------------

    "navbar": "navbar-dark navbar-primary",

    "brand_colour": "navbar-primary",

    # ------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------

    "sidebar": "sidebar-dark-primary",

    "sidebar_nav_small_text": False,

    "sidebar_disable_expand": False,

    "sidebar_nav_child_indent": True,

    "sidebar_nav_compact_style": False,

    "sidebar_nav_legacy_style": False,

    "sidebar_nav_flat_style": False,

    # ------------------------------------------------------
    # Accent
    # ------------------------------------------------------

    "accent": "accent-primary",

    # ------------------------------------------------------
    # Buttons
    # ------------------------------------------------------

    "button_classes": {

        "primary": "btn-primary",

        "secondary": "btn-secondary",

        "info": "btn-info",

        "warning": "btn-warning",

        "danger": "btn-danger",

        "success": "btn-success",

    }

}