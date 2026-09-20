from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.auth import get_user_model

from apps.sms_service.models import Contact, SmsCampaign, SmsRecipientLog

User = get_user_model()


class ContactModelTest(TestCase):
    def test_create_contact_normalizes_phone(self):
        contact = Contact.objects.create(
            full_name="رضا رضایی",
            phone_number="+989121112233",
            notes="مشتری حضوری",
        )
        self.assertEqual(contact.phone_number, "09121112233")
        self.assertIn("رضا رضایی", str(contact))

    def test_create_contact_persian_digits_normalized(self):
        contact = Contact.objects.create(
            full_name="مهدی حسینی",
            phone_number="۰۹۱۲۹۹۹۸۸۷۷",
        )
        self.assertEqual(contact.phone_number, "09129998877")

    def test_contact_phone_uniqueness_enforced(self):
        Contact.objects.create(
            full_name="کاربر اول",
            phone_number="09121112233",
        )
        with self.assertRaises((IntegrityError, ValidationError)):
            Contact.objects.create(
                full_name="کاربر دوم",
                phone_number="+989121112233",  # Will normalize to 09121112233
            )

    def test_contact_invalid_phone_validation(self):
        contact = Contact(
            full_name="نامعتبر",
            phone_number="02188888888",
        )
        with self.assertRaises(ValidationError):
            contact.full_clean()


class SmsCampaignAndLogModelTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="sms_admin",
            password="admin_password",
            first_name="مدیر",
            last_name="سامانه",
            phone_number="09120000001",
        )

    def test_create_campaign_and_logs(self):
        campaign = SmsCampaign.objects.create(
            sender=self.admin_user,
            message_body="پیامک تستی اطلاع‌رسانی",
            recipient_source=SmsCampaign.Source.MIXED,
            total_selected=2,
            total_deduplicated=2,
            successful_count=2,
            failed_count=0,
            status=SmsCampaign.Status.COMPLETED,
        )
        self.assertEqual(campaign.status, SmsCampaign.Status.COMPLETED)
        self.assertIn("کمپین #", str(campaign))

        log = SmsRecipientLog.objects.create(
            campaign=campaign,
            recipient_type=SmsRecipientLog.RecipientType.USER,
            user=self.admin_user,
            phone_number="09120000001",
            final_message="مدیر سامانه عزیز\nپیامک تستی اطلاع‌رسانی",
            status=SmsRecipientLog.Status.SUCCESS,
            provider_rec_id="987654321",
        )
        self.assertEqual(campaign.recipients.count(), 1)
        self.assertEqual(log.status, SmsRecipientLog.Status.SUCCESS)

