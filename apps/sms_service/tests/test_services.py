from unittest.mock import MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.sms_service.models import Contact, SmsCampaign, SmsRecipientLog
from apps.sms_service.services.campaign_service import send_campaign, prepare_campaign_preview
from apps.sms_service.services.provider import BaseSmsProvider, ProviderResult

User = get_user_model()


class MockCustomProvider(BaseSmsProvider):
    def __init__(self, succeed: bool = True, fail_for_phones: list[str] | None = None):
        self.succeed = succeed
        self.fail_for_phones = fail_for_phones or []
        self.calls: list[dict] = []

    def send_simple_sms(self, recipients: list[str], text: str, is_flash: bool = False) -> ProviderResult:
        self.calls.append({"recipients": recipients, "text": text, "is_flash": is_flash})
        for f_phone in self.fail_for_phones:
            if f_phone in recipients:
                return ProviderResult(success=False, error_code="MOCK_FAIL", error_message="ارسال با خطا مواجه شد.")

        if self.succeed:
            return ProviderResult(success=True, rec_id="123456789")
        return ProviderResult(success=False, error_code="GENERAL_FAIL", error_message="شکست در ارسال")


class CampaignServiceTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin_sender",
            password="pass",
            is_staff=True,
        )
        self.user1 = User.objects.create_user(
            username="user1",
            first_name="محمد",
            last_name="علوی",
            phone_number="09121111111",
        )
        self.user2 = User.objects.create_user(
            username="user2",
            first_name="",
            last_name="",
            phone_number="09122222222",
        )
        self.contact1 = Contact.objects.create(
            full_name="مخاطب الف",
            phone_number="09123333333",
        )

    def test_preview_deduplication_and_precedence(self):
        # Create a contact with the same phone number as user1
        contact_duplicate = Contact.objects.create(
            full_name="مخاطب با شماره کاربر ۱",
            phone_number="09121111111",
        )

        preview = prepare_campaign_preview(
            user_ids=[self.user1.id, self.user2.id],
            contact_ids=[self.contact1.id, contact_duplicate.id],
            message_body="تخفیف ویژه امروز",
        )

        self.assertEqual(preview["total_selected"], 4)
        self.assertEqual(preview["valid_count"], 3)  # user1, user2, contact1
        self.assertEqual(preview["duplicate_count"], 1)

        # Confirm duplicate was the contact, not the user
        dup = preview["duplicates"][0]
        self.assertEqual(dup.recipient_type, "contact")
        self.assertEqual(dup.phone_number, "09121111111")

    def test_send_campaign_personalized_and_plain(self):
        mock_provider = MockCustomProvider(succeed=True)

        result = send_campaign(
            sender_user=self.admin_user,
            user_ids=[self.user1.id, self.user2.id],
            contact_ids=[self.contact1.id],
            message_body="سفارش شما تایید شد.",
            provider=mock_provider,
        )

        campaign = result["campaign"]
        self.assertEqual(campaign.status, SmsCampaign.Status.COMPLETED)
        self.assertEqual(campaign.successful_count, 3)
        self.assertEqual(campaign.failed_count, 0)

        # Verify logs in DB
        logs = list(campaign.recipients.order_by("id"))
        self.assertEqual(len(logs), 3)

        # User1 personalized message
        user1_log = campaign.recipients.get(phone_number="09121111111")
        self.assertEqual(user1_log.recipient_type, SmsRecipientLog.RecipientType.USER)
        self.assertIn("محمد علوی عزیز", user1_log.final_message)
        self.assertIn("سفارش شما تایید شد.", user1_log.final_message)

        # User2 missing name fallback
        user2_log = campaign.recipients.get(phone_number="09122222222")
        self.assertEqual(user2_log.recipient_type, SmsRecipientLog.RecipientType.USER)
        self.assertIn("کاربر گرامی", user2_log.final_message)
        self.assertNotIn("عزیز", user2_log.final_message)

        # Contact1 plain message (no greeting)
        contact_log = campaign.recipients.get(phone_number="09123333333")
        self.assertEqual(contact_log.recipient_type, SmsRecipientLog.RecipientType.CONTACT)
        self.assertEqual(contact_log.final_message, "سفارش شما تایید شد.")

    def test_send_campaign_duplicate_handling_never_sends_twice(self):
        # Create a contact with same phone as user1
        Contact.objects.create(
            full_name="مخاطب تکراری",
            phone_number="09121111111",
        )
        mock_provider = MockCustomProvider(succeed=True)

        result = send_campaign(
            sender_user=self.admin_user,
            user_ids=[self.user1.id],
            contact_ids=list(Contact.objects.values_list("id", flat=True)),
            message_body="سلام",
            provider=mock_provider,
        )

        campaign = result["campaign"]
        # Total attempted sends to provider should only have 09121111111 ONCE
        sent_numbers = []
        for call in mock_provider.calls:
            sent_numbers.extend(call["recipients"])

        self.assertEqual(sent_numbers.count("09121111111"), 1)
        self.assertEqual(campaign.recipients.filter(status=SmsRecipientLog.Status.SKIPPED_DUPLICATE).count(), 1)

    def test_send_campaign_contact_batching_100_limit(self):
        # Create 105 contacts
        contacts_to_create = [
            Contact(full_name=f"مخاطب {i}", phone_number=f"0930{i:07d}")
            for i in range(105)
        ]
        Contact.objects.bulk_create(contacts_to_create)
        contact_ids = list(Contact.objects.filter(phone_number__startswith="0930").values_list("id", flat=True))

        mock_provider = MockCustomProvider(succeed=True)

        result = send_campaign(
            sender_user=self.admin_user,
            user_ids=[],
            contact_ids=contact_ids,
            message_body="پیام گروهی انبوه",
            provider=mock_provider,
        )

        # Verify batching: 105 contacts -> Batch 1 with 100, Batch 2 with 5
        self.assertEqual(len(mock_provider.calls), 2)
        self.assertEqual(len(mock_provider.calls[0]["recipients"]), 100)
        self.assertEqual(len(mock_provider.calls[1]["recipients"]), 5)
        self.assertEqual(result["successful_count"], 105)

    def test_send_campaign_partial_failure(self):
        # Fail user2 specifically
        mock_provider = MockCustomProvider(succeed=True, fail_for_phones=["09122222222"])

        result = send_campaign(
            sender_user=self.admin_user,
            user_ids=[self.user1.id, self.user2.id],
            contact_ids=[self.contact1.id],
            message_body="تست جزئی",
            provider=mock_provider,
        )

        campaign = result["campaign"]
        self.assertEqual(campaign.status, SmsCampaign.Status.PARTIAL_FAILURE)
        self.assertEqual(campaign.successful_count, 2)
        self.assertEqual(campaign.failed_count, 1)

