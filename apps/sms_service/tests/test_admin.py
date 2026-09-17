from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from apps.sms_service.models import Contact, SmsCampaign, SmsRecipientLog

User = get_user_model()


class SmsAdminSecurityAndWorkflowTest(TestCase):
    def setUp(self):
        # 1. Superuser
        self.superuser = User.objects.create_superuser(
            username="super_admin",
            password="admin_password",
            email="admin@sidoos.ir",
        )

        # 2. Staff with SMS permission
        self.staff_with_perm = User.objects.create_user(
            username="staff_allowed",
            password="staff_password",
            is_staff=True,
        )
        content_type = ContentType.objects.get_for_model(SmsCampaign)
        perm = Permission.objects.get(content_type=content_type, codename="add_smscampaign")
        self.staff_with_perm.user_permissions.add(perm)

        # 3. Staff without SMS permission
        self.staff_no_perm = User.objects.create_user(
            username="staff_denied",
            password="staff_password",
            is_staff=True,
        )

        # 4. Normal user
        self.normal_user = User.objects.create_user(
            username="regular_user",
            password="user_password",
            is_staff=False,
            phone_number="09121111111",
            first_name="کاربر",
            last_name="تستی",
        )

        # 5. Contact
        self.contact = Contact.objects.create(
            full_name="مخاطب تستی",
            phone_number="09122222222",
        )

        self.client = Client()
        self.send_url = reverse("admin:sms_service_send")

    def test_anonymous_user_redirected_to_login(self):
        resp = self.client.get(self.send_url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)

    def test_regular_user_forbidden_or_redirected(self):
        self.client.login(username="regular_user", password="user_password")
        resp = self.client.get(self.send_url)
        # Non-staff users get redirected by Django admin login check
        self.assertIn(resp.status_code, [302, 403])

    def test_staff_without_perm_forbidden(self):
        self.client.login(username="staff_denied", password="staff_password")
        resp = self.client.get(self.send_url)
        self.assertEqual(resp.status_code, 403)

    def test_staff_with_perm_access_granted(self):
        self.client.login(username="staff_allowed", password="staff_password")
        resp = self.client.get(self.send_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "مرکز ارسال پیامک")

    def test_get_request_never_triggers_sms(self):
        self.client.login(username="super_admin", password="admin_password")
        initial_count = SmsCampaign.objects.count()
        resp = self.client.get(self.send_url, {"message_body": "test", "selected_users": [self.normal_user.id]})
        self.assertEqual(resp.status_code, 200)
        # Zero campaigns created on GET
        self.assertEqual(SmsCampaign.objects.count(), initial_count)

    def test_post_step_preview_shows_confirmation(self):
        self.client.login(username="super_admin", password="admin_password")
        resp = self.client.post(
            self.send_url,
            {
                "step": "preview",
                "message_body": "پیامک اطلاع‌رسانی مهم",
                "selected_users": [self.normal_user.id],
                "selected_contacts": [self.contact.id],
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "تأیید و بازبینی نهایی ارسال پیامک")
        self.assertContains(resp, "پیامک اطلاع‌رسانی مهم")
        self.assertContains(resp, "کاربر تستی عزیز")

    def test_post_step_execute_sends_and_redirects(self):
        self.client.login(username="super_admin", password="admin_password")
        resp = self.client.post(
            self.send_url,
            {
                "step": "execute",
                "message_body": "سفارش شما ارسال گردید.",
                "selected_users": [self.normal_user.id],
                "selected_contacts": [self.contact.id],
            },
        )
        # Should redirect to campaign change page
        self.assertEqual(resp.status_code, 302)
        campaign = SmsCampaign.objects.latest("id")
        self.assertEqual(campaign.status, SmsCampaign.Status.COMPLETED)
        self.assertEqual(campaign.recipients.count(), 2)

    def test_csrf_protection_active(self):
        # A POST without CSRF client enforcement should fail if enforce_csrf_checks=True
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username="super_admin", password="admin_password")
        # Direct post without CSRF token
        resp = csrf_client.post(
            self.send_url,
            {"step": "preview", "message_body": "test"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_contact_admin_action_redirects_to_send(self):
        self.client.login(username="super_admin", password="admin_password")
        contact_changelist_url = reverse("admin:sms_service_contact_changelist")
        resp = self.client.post(
            contact_changelist_url,
            {
                "action": "send_sms_to_selected_contacts",
                "_selected_action": [str(self.contact.id)],
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(self.send_url, resp.url)
        self.assertIn(f"contact_ids={self.contact.id}", resp.url)

    def test_user_admin_action_redirects_to_send(self):
        self.client.login(username="super_admin", password="admin_password")
        user_changelist_url = reverse("admin:accounts_user_changelist")
        resp = self.client.post(
            user_changelist_url,
            {
                "action": "send_sms_to_selected_users",
                "_selected_action": [str(self.normal_user.id)],
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(self.send_url, resp.url)
        self.assertIn(f"user_ids={self.normal_user.id}", resp.url)

