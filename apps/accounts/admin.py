# apps/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

# Get the custom User model
User = get_user_model()


class UserAdmin(BaseUserAdmin):
    """
    Custom User Admin with extended fields
    """

    # Display these fields in the list view
    list_display = ('username', 'email', 'phone_number', 'first_name', 'last_name', 'is_staff', 'has_price_access')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'has_price_access', 'groups')
    search_fields = ('username', 'email', 'phone_number', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    # Fields to display when editing a user
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Custom Fields'), {'fields': ('has_price_access',)}),  # Added custom field
    )

    # Fields to display when creating a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone_number', 'password1', 'password2', 'has_price_access'),
        }),
    )

    # Make phone_number read-only in edit mode (optional)
    # readonly_fields = ('phone_number',)


# Register the User model with the custom admin
admin.site.register(User, UserAdmin)