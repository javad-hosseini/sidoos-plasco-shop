from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.urls import reverse

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
    actions = ('send_sms_to_selected_users',)

    # Fields to display when editing a user
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('اطلاعات شخصی', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('دسترسی‌ها', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('تاریخ‌های مهم', {'fields': ('last_login', 'date_joined')}),
        ('فیلدهای اختصاصی', {'fields': ('has_price_access',)}),  # Added custom field
    )

    # Fields to display when creating a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone_number', 'password1', 'password2', 'has_price_access'),
        }),
    )

    @admin.action(description="ارسال پیامک به کاربران انتخاب‌شده")
    def send_sms_to_selected_users(self, request, queryset):
        valid_users = queryset.exclude(phone_number__isnull=True).exclude(phone_number="")
        ids = list(valid_users.values_list("id", flat=True))
        if not ids:
            self.message_user(
                request,
                "هیچ‌کدام از کاربران انتخاب‌شده شماره موبایل ندارند.",
                level=messages.WARNING,
            )
            return
        url = reverse("admin:sms_service_send")
        return redirect(f"{url}?user_ids={','.join(map(str, ids))}")


# Register the User model with the custom admin
admin.site.register(User, UserAdmin)
