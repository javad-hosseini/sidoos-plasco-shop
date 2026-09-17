from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from django.contrib.auth import get_user_model
from django.conf import settings

from .models import Contact, SmsCampaign, SmsRecipientLog
from .forms import SmsComposerForm
from .services import (
    send_campaign,
    prepare_campaign_preview,
)

User = get_user_model()


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """
    Admin for Contact Book entries (non-registered individuals).
    """

    list_display = [
        "full_name",
        "phone_number_display",
        "notes_preview",
        "created_at",
        "updated_at",
    ]
    search_fields = ["full_name", "phone_number", "notes"]
    list_filter = ["created_at"]
    ordering = ["-created_at"]
    actions = ["send_sms_to_selected_contacts"]

    def phone_number_display(self, obj):
        return format_html('<span dir="ltr" class="font-weight-bold">{}</span>', obj.phone_number)

    phone_number_display.short_description = "شماره موبایل"
    phone_number_display.admin_order_field = "phone_number"

    def notes_preview(self, obj):
        if not obj.notes:
            return "-"
        return obj.notes[:50] + ("..." if len(obj.notes) > 50 else "")

    notes_preview.short_description = "یادداشت"

    @admin.action(description="ارسال پیامک به مخاطبین انتخاب‌شده")
    def send_sms_to_selected_contacts(self, request, queryset):
        ids = list(queryset.values_list("id", flat=True))
        if not ids:
            self.message_user(request, "هیچ مخاطبی انتخاب نشده است.", level=messages.WARNING)
            return
        send_url = reverse("admin:sms_service_send")
        return redirect(f"{send_url}?contact_ids={','.join(map(str, ids))}")


class SmsRecipientLogInline(admin.TabularInline):
    """
    Inline audit log for recipients within a campaign.
    """

    model = SmsRecipientLog
    extra = 0
    can_delete = False
    max_num = 0
    readonly_fields = [
        "recipient_type_display",
        "recipient_name_display",
        "phone_number",
        "final_message",
        "status_badge",
        "provider_rec_id",
        "error_message",
        "created_at",
    ]
    fields = [
        "recipient_type_display",
        "recipient_name_display",
        "phone_number",
        "status_badge",
        "provider_rec_id",
        "final_message",
        "error_message",
        "created_at",
    ]

    def has_add_permission(self, request, obj=None):
        return False

    def recipient_type_display(self, obj):
        if obj.recipient_type == SmsRecipientLog.RecipientType.USER:
            return format_html('<span class="badge badge-success">کاربر سایت</span>')
        return format_html('<span class="badge badge-info">دفترچه تلفن</span>')

    recipient_type_display.short_description = "نوع مخاطب"

    def recipient_name_display(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        if obj.contact:
            return obj.contact.full_name
        return "-"

    recipient_name_display.short_description = "نام مخاطب"

    def status_badge(self, obj):
        colors = {
            SmsRecipientLog.Status.SUCCESS: "success",
            SmsRecipientLog.Status.FAILED: "danger",
            SmsRecipientLog.Status.SKIPPED_DUPLICATE: "warning",
            SmsRecipientLog.Status.SKIPPED_INVALID: "secondary",
        }
        badge_cls = colors.get(obj.status, "secondary")
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            badge_cls,
            obj.get_status_display(),
        )

    status_badge.short_description = "وضعیت"


@admin.register(SmsCampaign)
class SmsCampaignAdmin(admin.ModelAdmin):
    """
    Admin interface for SMS Campaigns and access point for the Send SMS Center.
    """

    list_display = [
        "id",
        "sender_display",
        "short_message",
        "recipient_source_badge",
        "total_selected",
        "total_deduplicated",
        "successful_count",
        "failed_count",
        "status_badge",
        "created_at",
    ]
    list_filter = ["status", "recipient_source", "created_at"]
    search_fields = ["message_body", "sender__username", "sender__first_name", "sender__last_name"]
    ordering = ["-created_at"]
    readonly_fields = [
        "sender",
        "message_body",
        "recipient_source",
        "total_selected",
        "total_deduplicated",
        "successful_count",
        "failed_count",
        "status",
        "created_at",
    ]
    inlines = [SmsRecipientLogInline]

    def has_add_permission(self, request):
        # Prevent manual campaign creation via raw form; creation happens via Send SMS center
        return False

    def sender_display(self, obj):
        if not obj.sender:
            return "سیستم"
        return obj.sender.get_full_name() or obj.sender.username

    sender_display.short_description = "ارسال‌کننده"

    def recipient_source_badge(self, obj):
        badges = {
            SmsCampaign.Source.USERS: ("success", "کاربران سایت"),
            SmsCampaign.Source.CONTACTS: ("info", "دفترچه تلفن"),
            SmsCampaign.Source.MIXED: ("primary", "ترکیبی"),
        }
        color, label = badges.get(obj.recipient_source, ("secondary", obj.get_recipient_source_display()))
        return format_html('<span class="badge badge-{}">{}</span>', color, label)

    recipient_source_badge.short_description = "منبع"

    def status_badge(self, obj):
        colors = {
            SmsCampaign.Status.COMPLETED: "success",
            SmsCampaign.Status.PARTIAL_FAILURE: "warning",
            SmsCampaign.Status.FAILED: "danger",
            SmsCampaign.Status.PENDING: "info",
        }
        color = colors.get(obj.status, "secondary")
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_status_display())

    status_badge.short_description = "وضعیت"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "send/",
                self.admin_site.admin_view(self.sms_send_view),
                name="sms_service_send",
            ),
        ]
        return custom_urls + urls

    def sms_send_view(self, request):
        """
        Interactive Send SMS Center view with selection, validation, confirmation, and execution.
        """
        # Authorization check
        if not (request.user.is_staff and (request.user.is_superuser or request.user.has_perm("sms_service.add_smscampaign"))):
            raise PermissionDenied("شما مجوز دسترسی به مرکز ارسال پیامک را ندارید.")

        is_console_mode = getattr(settings, "SMS_CONSOLE_MODE", False) or not (
            getattr(settings, "MELIPAYAMAK_USERNAME", "")
            and getattr(settings, "MELIPAYAMAK_PASSWORD", "")
            and getattr(settings, "MELIPAYAMAK_FROM_NUMBER", "")
        )

        if request.method == "POST":
            step = request.POST.get("step", "preview")
            message_body = request.POST.get("message_body", "").strip()

            raw_user_ids = request.POST.getlist("selected_users")
            raw_contact_ids = request.POST.getlist("selected_contacts")

            user_ids = [int(uid) for uid in raw_user_ids if str(uid).isdigit()]
            contact_ids = [int(cid) for cid in raw_contact_ids if str(cid).isdigit()]

            # Validation
            form = SmsComposerForm(request.POST)
            if not form.is_valid():
                messages.error(request, "لطفاً متن پیامک معتبری وارد کنید.")
                return self._render_composer(
                    request,
                    form=form,
                    preselected_user_ids=user_ids,
                    preselected_contact_ids=contact_ids,
                    is_console_mode=is_console_mode,
                )

            if not user_ids and not contact_ids:
                messages.error(request, "لطفاً حداقل یک مخاطب یا کاربر را انتخاب کنید.")
                return self._render_composer(
                    request,
                    form=form,
                    preselected_user_ids=user_ids,
                    preselected_contact_ids=contact_ids,
                    is_console_mode=is_console_mode,
                )

            # Step 1: Confirmation & Review Preview
            if step == "preview":
                preview = prepare_campaign_preview(user_ids, contact_ids, message_body)
                if preview["valid_count"] == 0:
                    messages.error(
                        request,
                        "هیچ شماره موبایل معتبری در میان مخاطبین انتخاب‌شده وجود ندارد.",
                    )
                    return self._render_composer(
                        request,
                        form=form,
                        preselected_user_ids=user_ids,
                        preselected_contact_ids=contact_ids,
                        is_console_mode=is_console_mode,
                    )

                context = {
                    **self.admin_site.each_context(request),
                    "title": "تأیید و بازبینی نهایی ارسال پیامک",
                    "preview": preview,
                    "message_body": message_body,
                    "user_ids": user_ids,
                    "contact_ids": contact_ids,
                }
                return render(request, "admin/sms_service/send_confirm.html", context)

            # Step 2: Final Execute POST
            elif step == "execute":
                result = send_campaign(
                    sender_user=request.user,
                    user_ids=user_ids,
                    contact_ids=contact_ids,
                    message_body=message_body,
                )
                campaign = result["campaign"]

                if campaign.status == SmsCampaign.Status.COMPLETED:
                    messages.success(
                        request,
                        f"کمپین پیامک با موفقیت ارسال شد: {result['successful_count']} پیامک با موفقیت تحویل درگاه گردید.",
                    )
                elif campaign.status == SmsCampaign.Status.PARTIAL_FAILURE:
                    messages.warning(
                        request,
                        f"کمپین پیامک با موفقیت جزئی ارسال شد: {result['successful_count']} ارسال موفق، {result['failed_count']} ارسال ناموفق.",
                    )
                else:
                    messages.error(
                        request,
                        f"ارسال کمپین پیامک ناموفق بود. تمام {result['failed_count']} تلاش با خطا مواجه شدند.",
                    )

                if result["skipped_duplicates"] > 0:
                    messages.info(
                        request,
                        f"{result['skipped_duplicates']} شماره تکراری حذف شدند و فقط یک‌بار پیامک دریافت کردند.",
                    )

                return redirect("admin:sms_service_smscampaign_change", object_id=campaign.id)

        # GET request: Render composer with pre-selected IDs if provided in query params
        preselected_users = []
        user_param = request.GET.get("user_ids", "")
        if user_param:
            preselected_users = [int(x) for x in user_param.split(",") if x.strip().isdigit()]

        preselected_contacts = []
        contact_param = request.GET.get("contact_ids", "")
        if contact_param:
            preselected_contacts = [int(x) for x in contact_param.split(",") if x.strip().isdigit()]

        form = SmsComposerForm()
        return self._render_composer(
            request,
            form=form,
            preselected_user_ids=preselected_users,
            preselected_contact_ids=preselected_contacts,
            is_console_mode=is_console_mode,
        )

    def _render_composer(self, request, form, preselected_user_ids, preselected_contact_ids, is_console_mode):
        # Fetch registered users with a phone number
        users = list(
            User.objects.filter(phone_number__isnull=False)
            .exclude(phone_number="")
            .order_by("-date_joined")[:500]
        )
        contacts = list(Contact.objects.all().order_by("-created_at")[:500])

        context = {
            **self.admin_site.each_context(request),
            "title": "مرکز ارسال پیامک",
            "form": form,
            "users": users,
            "contacts": contacts,
            "preselected_user_ids": preselected_user_ids,
            "preselected_contact_ids": preselected_contact_ids,
            "is_console_mode": is_console_mode,
        }
        return render(request, "admin/sms_service/send_sms.html", context)


@admin.register(SmsRecipientLog)
class SmsRecipientLogAdmin(admin.ModelAdmin):
    """
    Searchable audit log for individual SMS messages.
    """

    list_display = [
        "id",
        "campaign_link",
        "recipient_type",
        "recipient_name_display",
        "phone_number",
        "status_badge",
        "provider_rec_id",
        "created_at",
    ]
    list_filter = ["status", "recipient_type", "created_at"]
    search_fields = ["phone_number", "final_message", "provider_rec_id", "user__username", "contact__full_name"]
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def campaign_link(self, obj):
        url = reverse("admin:sms_service_smscampaign_change", args=[obj.campaign.id])
        return format_html('<a href="{}">کمپین #{}</a>', url, obj.campaign.id)

    campaign_link.short_description = "کمپین"

    def recipient_name_display(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        if obj.contact:
            return obj.contact.full_name
        return "-"

    recipient_name_display.short_description = "نام مخاطب"

    def status_badge(self, obj):
        colors = {
            SmsRecipientLog.Status.SUCCESS: "success",
            SmsRecipientLog.Status.FAILED: "danger",
            SmsRecipientLog.Status.SKIPPED_DUPLICATE: "warning",
            SmsRecipientLog.Status.SKIPPED_INVALID: "secondary",
        }
        color = colors.get(obj.status, "secondary")
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_status_display())

    status_badge.short_description = "وضعیت"
