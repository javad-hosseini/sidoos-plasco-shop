"""
Admin configuration for the support application.

Provides user-friendly admin interface for support staff to manage
tickets, messages, and attachments.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from .models import Ticket, TicketMessage, TicketAttachment
from .services import send_support_message, close_ticket, reopen_ticket


class TicketMessageInline(admin.TabularInline):
    """
    Inline display of messages within a ticket.
    """

    model = TicketMessage
    extra = 0
    readonly_fields = ["sender", "message", "created_at"]
    fields = ["sender", "message", "created_at"]
    can_delete = False
    max_num = 0

    def has_add_permission(self, request, obj=None):
        """Prevent adding messages directly through inline."""
        return False


class TicketAttachmentInline(admin.TabularInline):
    """
    Inline display of attachments within a message.
    """

    model = TicketAttachment
    extra = 0
    readonly_fields = ["file", "original_name", "created_at"]
    fields = ["file", "original_name", "created_at"]
    can_delete = False
    max_num = 0

    def has_add_permission(self, request, obj=None):
        """Prevent adding attachments directly through inline."""
        return False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    """
    Admin interface for managing support tickets.
    """

    list_display = [
        "tracking_code_display",
        "title",
        "user",
        "subject",
        "status_display",
        "created_at",
        "updated_at",
        "message_count",
    ]

    list_filter = [
        "status",
        "subject",
        "created_at",
    ]

    search_fields = [
        "tracking_code",
        "title",
        "user__username",
        "user__email",
    ]

    ordering = ["-created_at"]

    readonly_fields = [
        "tracking_code",
        "user",
        "title",
        "subject",
        "created_at",
        "updated_at",
    ]

    list_per_page = 25

    inlines = [TicketMessageInline]

    fieldsets = [
        (
            "اطلاعات تیکت",
            {
                "fields": (
                    "tracking_code",
                    "user",
                    "title",
                    "subject",
                    "status",
                ),
            },
        ),
        (
            "زمان‌بندی",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    ]

    actions = [
        "close_tickets",
        "reopen_tickets",
    ]

    def tracking_code_display(self, obj):
        """
        Display tracking code prominently.
        """
        return format_html(
            '<span style="font-weight: bold; font-size: 1.1em;">{}</span>',
            obj.tracking_code,
        )

    tracking_code_display.short_description = "کد پیگیری"
    tracking_code_display.admin_order_field = "tracking_code"

    def status_display(self, obj):
        """
        Display status with color coding.
        """
        status_colors = {
            Ticket.Status.WAITING_FOR_SUPPORT: "#E87932",  # Orange
            Ticket.Status.WAITING_FOR_USER: "#245C43",      # Green
            Ticket.Status.CLOSED: "#6E756F",                # Gray
        }

        color = status_colors.get(obj.status, "#6E756F")

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 4px 10px; border-radius: 12px; '
            'font-size: 0.85em;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_display.short_description = "وضعیت"
    status_display.admin_order_field = "status"

    def message_count(self, obj):
        """
        Display the number of messages in the ticket.
        """
        count = obj.messages.count()
        return format_html(
            '<span style="font-size: 0.9em;">{} پیام</span>',
            count,
        )

    message_count.short_description = "تعداد پیام‌ها"

    def save_model(self, request, obj, form, change):
        """
        Handle special actions when saving ticket from admin.
        """
        if change:
            old_obj = Ticket.objects.get(pk=obj.pk)
            if old_obj.status != obj.status:
                if obj.status == Ticket.Status.CLOSED:
                    close_ticket(obj)
                elif old_obj.status == Ticket.Status.CLOSED and obj.status != Ticket.Status.CLOSED:
                    reopen_ticket(obj)
                else:
                    super().save_model(request, obj, form, change)
                return
        super().save_model(request, obj, form, change)

    @admin.action(description="بستن تیکت‌های انتخاب شده")
    def close_tickets(self, request, queryset):
        """
        Close selected tickets.
        """
        count = 0
        for ticket in queryset:
            if not ticket.is_closed:
                close_ticket(ticket)
                count += 1
        self.message_user(request, f"{count} تیکت بسته شد.")

    @admin.action(description="باز کردن تیکت‌های انتخاب شده")
    def reopen_tickets(self, request, queryset):
        """
        Reopen selected closed tickets.
        """
        count = 0
        for ticket in queryset:
            if ticket.is_closed:
                reopen_ticket(ticket)
                count += 1
        self.message_user(request, f"{count} تیکت باز شد.")


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    """
    Admin interface for managing ticket messages.
    """

    list_display = [
        "ticket_tracking_code",
        "sender",
        "short_preview_display",
        "created_at",
        "attachment_count",
    ]

    list_filter = ["created_at"]

    search_fields = [
        "ticket__tracking_code",
        "sender__username",
        "message",
    ]

    ordering = ["-created_at"]

    readonly_fields = [
        "ticket",
        "sender",
        "message",
        "created_at",
        "updated_at",
    ]

    list_per_page = 50

    inlines = [TicketAttachmentInline]

    def ticket_tracking_code(self, obj):
        """
        Display the ticket tracking code.
        """
        return obj.ticket.tracking_code

    ticket_tracking_code.short_description = "کد پیگیری"
    ticket_tracking_code.admin_order_field = "ticket__tracking_code"

    def short_preview_display(self, obj):
        """
        Display a short preview of the message.
        """
        return obj.short_preview

    short_preview_display.short_description = "پیش‌نمایش پیام"

    def attachment_count(self, obj):
        """
        Display the number of attachments.
        """
        count = obj.attachments.count()
        if count > 0:
            return format_html(
                '<span style="color: #245C43;">{} فایل</span>',
                count,
            )
        return "-"

    attachment_count.short_description = "پیوست‌ها"


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    """
    Admin interface for managing ticket attachments.
    """

    list_display = [
        "original_name",
        "ticket_tracking_code",
        "file_link",
        "created_at",
    ]

    search_fields = [
        "original_name",
        "message__ticket__tracking_code",
    ]

    ordering = ["-created_at"]

    readonly_fields = [
        "message",
        "file",
        "original_name",
        "created_at",
    ]

    list_per_page = 50

    def ticket_tracking_code(self, obj):
        """
        Display the ticket tracking code.
        """
        return obj.message.ticket.tracking_code

    ticket_tracking_code.short_description = "کد پیگیری"

    def file_link(self, obj):
        """
        Display a link to the uploaded file.
        """
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">دانلود</a>',
                obj.file.url,
            )
        return "-"

    file_link.short_description = "فایل"