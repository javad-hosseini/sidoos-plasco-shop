"""
Campaign management service.

Handles recipient resolution, phone normalization, cross-source deduplication,
batch partitioning, concurrent sending for personalized messages, and audit logging.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import logging
from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.sms_service.models import Contact, SmsCampaign, SmsRecipientLog
from apps.sms_service.utils import (
    normalize_phone_number,
    format_personalized_message,
)
from .provider import BaseSmsProvider, ProviderResult, get_sms_provider

logger = logging.getLogger(__name__)
User = get_user_model()

# Max recipients allowed per MeliPayamak Simple SMS call
PROVIDER_BATCH_LIMIT = 100


@dataclass
class ResolvedRecipient:
    recipient_type: str  # 'user' or 'contact'
    id: int
    name: str
    phone_number: str
    message: str
    obj: Any
    is_valid: bool = True
    invalid_reason: str = ""
    is_duplicate: bool = False


def prepare_campaign_preview(
    user_ids: list[int],
    contact_ids: list[int],
    message_body: str,
) -> dict[str, Any]:
    """
    Resolve recipients, perform deduplication, and return preview metrics
    without initiating any actual SMS sending or database writes.
    """
    users = list(User.objects.filter(id__in=user_ids))
    contacts = list(Contact.objects.filter(id__in=contact_ids))

    seen_phones: dict[str, ResolvedRecipient] = {}
    valid_recipients: list[ResolvedRecipient] = []
    duplicate_recipients: list[ResolvedRecipient] = []
    invalid_recipients: list[ResolvedRecipient] = []

    # 1. Process Registered Users first (User takes precedence)
    for u in users:
        raw_phone = getattr(u, "phone_number", "") or ""
        try:
            norm_phone = normalize_phone_number(raw_phone)
            personalized_msg = format_personalized_message(u, message_body)
            full_name = u.get_full_name() or u.username

            rec = ResolvedRecipient(
                recipient_type="user",
                id=u.id,
                name=full_name,
                phone_number=norm_phone,
                message=personalized_msg,
                obj=u,
            )

            if norm_phone in seen_phones:
                rec.is_duplicate = True
                duplicate_recipients.append(rec)
            else:
                seen_phones[norm_phone] = rec
                valid_recipients.append(rec)
        except ValidationError as e:
            invalid_recipients.append(
                ResolvedRecipient(
                    recipient_type="user",
                    id=u.id,
                    name=u.get_full_name() or u.username,
                    phone_number=raw_phone,
                    message="",
                    obj=u,
                    is_valid=False,
                    invalid_reason=str(e),
                )
            )

    # 2. Process Contact Book entries
    clean_body = message_body.strip()
    for c in contacts:
        raw_phone = c.phone_number or ""
        try:
            norm_phone = normalize_phone_number(raw_phone)
            rec = ResolvedRecipient(
                recipient_type="contact",
                id=c.id,
                name=c.full_name,
                phone_number=norm_phone,
                message=clean_body,
                obj=c,
            )

            if norm_phone in seen_phones:
                # Deduplicated: User took precedence or another contact has same phone
                rec.is_duplicate = True
                duplicate_recipients.append(rec)
            else:
                seen_phones[norm_phone] = rec
                valid_recipients.append(rec)
        except ValidationError as e:
            invalid_recipients.append(
                ResolvedRecipient(
                    recipient_type="contact",
                    id=c.id,
                    name=c.full_name,
                    phone_number=raw_phone,
                    message="",
                    obj=c,
                    is_valid=False,
                    invalid_reason=str(e),
                )
            )

    sample_user_msg = ""
    for r in valid_recipients:
        if r.recipient_type == "user":
            sample_user_msg = r.message
            break

    return {
        "total_selected": len(users) + len(contacts),
        "total_users": len(users),
        "total_contacts": len(contacts),
        "valid_recipients": valid_recipients,
        "valid_count": len(valid_recipients),
        "duplicates": duplicate_recipients,
        "duplicate_count": len(duplicate_recipients),
        "invalid": invalid_recipients,
        "invalid_count": len(invalid_recipients),
        "sample_user_message": sample_user_msg,
        "sample_contact_message": clean_body,
    }


def send_campaign(
    sender_user,
    user_ids: list[int],
    contact_ids: list[int],
    message_body: str,
    provider: BaseSmsProvider | None = None,
    max_workers: int = 5,
) -> dict[str, Any]:
    """
    Execute a full SMS campaign:
    - Resolves and deduplicates recipients
    - Creates SmsCampaign record
    - Sends personalized user messages concurrently via ThreadPoolExecutor
    - Sends contact messages in chunks of up to 100 via provider batching
    - Records detailed SmsRecipientLog for every recipient
    - Updates campaign statistics and status
    """
    if provider is None:
        provider = get_sms_provider()

    preview = prepare_campaign_preview(user_ids, contact_ids, message_body)
    valid_recipients: list[ResolvedRecipient] = preview["valid_recipients"]
    duplicate_recipients: list[ResolvedRecipient] = preview["duplicates"]
    invalid_recipients: list[ResolvedRecipient] = preview["invalid"]

    # Determine recipient source label
    has_users = bool(user_ids)
    has_contacts = bool(contact_ids)
    if has_users and has_contacts:
        source = SmsCampaign.Source.MIXED
    elif has_users:
        source = SmsCampaign.Source.USERS
    else:
        source = SmsCampaign.Source.CONTACTS

    with transaction.atomic():
        campaign = SmsCampaign.objects.create(
            sender=sender_user,
            message_body=message_body.strip(),
            recipient_source=source,
            total_selected=preview["total_selected"],
            total_deduplicated=preview["valid_count"],
            status=SmsCampaign.Status.PENDING,
        )

        # Log invalid recipients immediately
        for inv in invalid_recipients:
            SmsRecipientLog.objects.create(
                campaign=campaign,
                recipient_type=inv.recipient_type,
                user=inv.obj if inv.recipient_type == "user" else None,
                contact=inv.obj if inv.recipient_type == "contact" else None,
                phone_number=inv.phone_number or "بدون شماره",
                final_message="",
                status=SmsRecipientLog.Status.SKIPPED_INVALID,
                error_message=inv.invalid_reason or "شماره موبایل نامعتبر است.",
            )

        # Log duplicate recipients
        for dup in duplicate_recipients:
            SmsRecipientLog.objects.create(
                campaign=campaign,
                recipient_type=dup.recipient_type,
                user=dup.obj if dup.recipient_type == "user" else None,
                contact=dup.obj if dup.recipient_type == "contact" else None,
                phone_number=dup.phone_number,
                final_message=dup.message,
                status=SmsRecipientLog.Status.SKIPPED_DUPLICATE,
                error_message="شماره در این کمپین تکراری بود و یک‌بار برای اولویت بالاتر ارسال شد.",
            )

    successful_count = 0
    failed_count = 0

    # Separate valid recipients into users (personalized) and contacts (batch identical)
    user_recipients = [r for r in valid_recipients if r.recipient_type == "user"]
    contact_recipients = [r for r in valid_recipients if r.recipient_type == "contact"]

    # 1. Send personalized messages to registered users concurrently
    if user_recipients:
        def _send_single_user(recipient: ResolvedRecipient) -> tuple[ResolvedRecipient, ProviderResult]:
            res = provider.send_simple_sms(
                recipients=[recipient.phone_number],
                text=recipient.message,
            )
            return recipient, res

        workers = min(max_workers, len(user_recipients))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_rec = {
                executor.submit(_send_single_user, rec): rec
                for rec in user_recipients
            }
            for future in as_completed(future_to_rec):
                rec, result = future.result()
                status = (
                    SmsRecipientLog.Status.SUCCESS
                    if result.success
                    else SmsRecipientLog.Status.FAILED
                )
                if result.success:
                    successful_count += 1
                else:
                    failed_count += 1

                SmsRecipientLog.objects.create(
                    campaign=campaign,
                    recipient_type=rec.recipient_type,
                    user=rec.obj,
                    phone_number=rec.phone_number,
                    final_message=rec.message,
                    status=status,
                    provider_rec_id=result.rec_id,
                    error_code=result.error_code,
                    error_message=result.error_message,
                )

    # 2. Send identical messages to contact book recipients concurrently
    if contact_recipients:
        clean_text = message_body.strip()

        def _send_single_contact(recipient: ResolvedRecipient) -> tuple[ResolvedRecipient, ProviderResult]:
            res = provider.send_simple_sms(
                recipients=[recipient.phone_number],
                text=clean_text,
            )
            return recipient, res

        workers = min(max_workers, len(contact_recipients))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_rec = {
                executor.submit(_send_single_contact, rec): rec
                for rec in contact_recipients
            }
            for future in as_completed(future_to_rec):
                rec, result = future.result()
                status = (
                    SmsRecipientLog.Status.SUCCESS
                    if result.success
                    else SmsRecipientLog.Status.FAILED
                )
                if result.success:
                    successful_count += 1
                else:
                    failed_count += 1

                SmsRecipientLog.objects.create(
                    campaign=campaign,
                    recipient_type=rec.recipient_type,
                    contact=rec.obj,
                    phone_number=rec.phone_number,
                    final_message=clean_text,
                    status=status,
                    provider_rec_id=result.rec_id,
                    error_code=result.error_code,
                    error_message=result.error_message,
                )

    # 3. Update campaign totals and final status
    total_attempted = preview["valid_count"]
    if total_attempted == 0:
        campaign.status = SmsCampaign.Status.FAILED
    elif successful_count == total_attempted:
        campaign.status = SmsCampaign.Status.COMPLETED
    elif successful_count == 0:
        campaign.status = SmsCampaign.Status.FAILED
    else:
        campaign.status = SmsCampaign.Status.PARTIAL_FAILURE

    campaign.successful_count = successful_count
    campaign.failed_count = failed_count
    campaign.save(update_fields=["status", "successful_count", "failed_count"])

    return {
        "campaign": campaign,
        "total_selected": preview["total_selected"],
        "total_deduplicated": preview["valid_count"],
        "successful_count": successful_count,
        "failed_count": failed_count,
        "skipped_duplicates": preview["duplicate_count"],
        "skipped_invalid": preview["invalid_count"],
        "status": campaign.status,
    }

