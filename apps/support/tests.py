"""
Tests for the support application.

Tests cover:
- Ticket creation and tracking code generation
- Authorization and ownership
- Message flow and business rules
- Closed ticket behavior
- Attachment validation

python manage.py test apps.support

"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, RequestFactory
from django.urls import reverse
from PIL import Image
from io import BytesIO

from .models import Ticket, TicketMessage, TicketAttachment
from .services import (
    generate_tracking_code,
    create_ticket,
    send_customer_message,
    send_support_message,
    close_ticket,
    reopen_ticket,
)
from .validators import validate_ticket_attachment


User = get_user_model()


class TicketModelTests(TestCase):
    """
    Test the Ticket model and tracking code generation.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
        )
        self.staff_user = User.objects.create_user(
            username="staffuser",
            password="testpass123",
            is_staff=True,
        )

    def test_tracking_code_generation(self):
        """Test that tracking code is 6 digits."""
        code = generate_tracking_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_tracking_code_uniqueness(self):
        """Test that generated codes are unique."""
        codes = set()
        for _ in range(10):
            code = generate_tracking_code()
            self.assertNotIn(code, codes)
            codes.add(code)

    def test_ticket_creation(self):
        """Test creating a ticket with initial message."""
        ticket = create_ticket(
            user=self.user,
            title="Test Ticket",
            subject=Ticket.Subject.ORDER,
            message_text="This is a test message.",
        )

        self.assertEqual(ticket.user, self.user)
        self.assertEqual(ticket.status, Ticket.Status.WAITING_FOR_SUPPORT)
        self.assertTrue(ticket.tracking_code.isdigit())
        self.assertEqual(len(ticket.tracking_code), 6)
        self.assertEqual(ticket.messages.count(), 1)

    def test_ticket_str_method(self):
        """Test string representation."""
        ticket = create_ticket(
            user=self.user,
            title="Test Ticket",
            subject=Ticket.Subject.ORDER,
            message_text="Test message",
        )
        self.assertIn(ticket.tracking_code, str(ticket))
        self.assertIn(ticket.title, str(ticket))


class TicketAuthorizationTests(TestCase):
    """
    Test ticket ownership and authorization.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
        )
        self.other_user = User.objects.create_user(
            username="otheruser",
            password="testpass123",
        )

        self.ticket = create_ticket(
            user=self.user,
            title="Test Ticket",
            subject=Ticket.Subject.ORDER,
            message_text="Test message",
        )

    def test_ticket_ownership_verification(self):
        """Test that services verify ticket ownership."""
        # Customer sending message on own ticket should work
        # First, support needs to reply to change status
        support_user = User.objects.create_user(
            username="support",
            password="testpass123",
            is_staff=True,
        )
        send_support_message(
            ticket=self.ticket,
            user=support_user,
            message_text="Support reply",
        )

        # Now customer can send
        message = send_customer_message(
            ticket=self.ticket,
            user=self.user,
            message_text="Customer reply",
        )
        self.assertIsNotNone(message)

    def test_non_owner_cannot_send_message(self):
        """Test that non-owner cannot send message on someone else's ticket."""
        support_user = User.objects.create_user(
            username="support",
            password="testpass123",
            is_staff=True,
        )
        send_support_message(
            ticket=self.ticket,
            user=support_user,
            message_text="Support reply",
        )

        # Other user tries to send message
        with self.assertRaises(ValidationError):
            send_customer_message(
                ticket=self.ticket,
                user=self.other_user,
                message_text="Trying to hijack ticket",
            )


class TicketMessageFlowTests(TestCase):
    """
    Test the message flow and business rules.
    """

    def setUp(self):
        self.customer = User.objects.create_user(
            username="customer",
            password="testpass123",
        )
        self.support_staff = User.objects.create_user(
            username="support",
            password="testpass123",
            is_staff=True,
        )

        self.ticket = create_ticket(
            user=self.customer,
            title="Test Flow",
            subject=Ticket.Subject.PRODUCT,
            message_text="Initial message",
        )

    def test_initial_status(self):
        """Test initial ticket status."""
        self.assertEqual(self.ticket.status, Ticket.Status.WAITING_FOR_SUPPORT)

    def test_customer_cannot_send_twice(self):
        """Test that customer cannot send consecutive messages."""
        with self.assertRaises(ValidationError):
            send_customer_message(
                ticket=self.ticket,
                user=self.customer,
                message_text="Second message",
            )

    def test_non_staff_cannot_send_support_message(self):
        non_staff = User.objects.create_user(
            username="notstaff",
            password="testpass123",
        )
        with self.assertRaises(ValidationError):
            send_support_message(
                ticket=self.ticket,
                user=non_staff,
                message_text="Unauthorized support reply",
            )

    def test_support_can_reply(self):
        """Test that support can reply to waiting ticket."""
        message = send_support_message(
            ticket=self.ticket,
            user=self.support_staff,
            message_text="Support reply",
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.WAITING_FOR_USER)

    def test_full_conversation_flow(self):
        """Test complete conversation flow."""
        # Support replies
        send_support_message(
            ticket=self.ticket,
            user=self.support_staff,
            message_text="How can I help?",
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.WAITING_FOR_USER)

        # Customer replies
        send_customer_message(
            ticket=self.ticket,
            user=self.customer,
            message_text="I have a problem.",
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.WAITING_FOR_SUPPORT)

        # Support replies again
        send_support_message(
            ticket=self.ticket,
            user=self.support_staff,
            message_text="Let me help you.",
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.WAITING_FOR_USER)


class TicketClosedTests(TestCase):
    """
    Test closed ticket behavior.
    """

    def setUp(self):
        self.customer = User.objects.create_user(
            username="customer",
            password="testpass123",
        )
        self.support_staff = User.objects.create_user(
            username="support",
            password="testpass123",
            is_staff=True,
        )

        self.ticket = create_ticket(
            user=self.customer,
            title="Test Closed",
            subject=Ticket.Subject.ACCOUNT,
            message_text="Initial message",
        )

    def test_close_ticket(self):
        """Test closing a ticket."""
        close_ticket(self.ticket)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.CLOSED)

    def test_customer_cannot_message_closed_ticket(self):
        """Test that customer cannot message a closed ticket."""
        close_ticket(self.ticket)
        with self.assertRaises(ValidationError):
            send_customer_message(
                ticket=self.ticket,
                user=self.customer,
                message_text="Hello?",
            )

    def test_reopen_ticket(self):
        """Test reopening a closed ticket."""
        close_ticket(self.ticket)
        reopen_ticket(self.ticket)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.WAITING_FOR_USER)

    def test_support_cannot_message_closed_ticket(self):
        """Test that support cannot message a closed ticket."""
        close_ticket(self.ticket)
        with self.assertRaises(ValidationError):
            send_support_message(
                ticket=self.ticket,
                user=self.support_staff,
                message_text="Hello?",
            )


class TicketAttachmentTests(TestCase):
    """
    Test attachment validation and security.
    """

    def create_test_image(self):
        """Create a test image file."""
        img = Image.new("RGB", (100, 100), color="red")
        img_io = BytesIO()
        img.save(img_io, format="JPEG")
        img_io.seek(0)
        return SimpleUploadedFile(
            "test.jpg",
            img_io.read(),
            content_type="image/jpeg",
        )

    def create_test_pdf(self):
        """Create a test PDF file."""
        content = b"%PDF-1.4 test content"
        return SimpleUploadedFile(
            "test.pdf",
            content,
            content_type="application/pdf",
        )

    def test_valid_jpg_attachment(self):
        """Test that valid JPG passes validation."""
        file = self.create_test_image()
        try:
            category = validate_ticket_attachment(file)
            self.assertEqual(category, "image")
        except ValidationError:
            self.fail("Valid JPG should pass validation")

    def test_valid_pdf_attachment(self):
        """Test that valid PDF passes validation."""
        file = self.create_test_pdf()
        try:
            category = validate_ticket_attachment(file)
            self.assertEqual(category, "document")
        except ValidationError:
            self.fail("Valid PDF should pass validation")

    def test_invalid_extension(self):
        """Test that invalid extension is rejected."""
        file = SimpleUploadedFile(
            "test.exe",
            b"malicious content",
            content_type="application/octet-stream",
        )
        with self.assertRaises(ValidationError):
            validate_ticket_attachment(file)

    def test_invalid_mime_type(self):
        """Test that mismatched MIME type is rejected."""
        file = SimpleUploadedFile(
            "test.jpg",
            b"not really an image",
            content_type="application/x-php",
        )
        with self.assertRaises(ValidationError):
            validate_ticket_attachment(file)

    def test_oversized_image(self):
        """Test that oversized image is rejected."""
        # Create a large file (> 5MB)
        content = b"0" * (5 * 1024 * 1024 + 1)
        file = SimpleUploadedFile(
            "large.jpg",
            content,
            content_type="image/jpeg",
        )
        with self.assertRaises(ValidationError):
            validate_ticket_attachment(file)