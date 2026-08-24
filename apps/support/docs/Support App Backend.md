# Support App Documentation

## Overview

The `support` app implements a ticket-based customer support system for Sidoos. Authenticated users can create support tickets, view their ticket history, and converse with support staff. The system enforces a strict turn‑based messaging rule: a customer cannot send consecutive messages without a support reply.

Key features:
- Unique 6‑digit tracking codes.
- Server‑side message‑turn enforcement.
- Secure file attachments (images and PDF only, size‑limited).
- Owner‑based authorization.
- Admin interface for support staff.

---

## File Structure

| File | Purpose |
|------|---------|
| `models.py` | Defines `Ticket`, `TicketMessage`, and `TicketAttachment` models. |
| `services.py` | Central business logic: ticket creation, message sending, closing/reopening. |
| `views.py` | Customer‑facing views: ticket list, create, and detail. |
| `forms.py` | Forms for creating tickets and sending messages, including multi‑file upload handling. |
| `urls.py` | URL patterns with a custom converter for 6‑digit tracking codes. |
| `validators.py` | File validation helpers (extension, MIME, size, image content). |
| `admin.py` | Admin configuration for tickets, messages, and attachments. |
| `apps.py` | Django app configuration. |
| `tests.py` | Unit tests covering business logic, authorization, and validation. |

---

## Detailed File Descriptions

### `models.py`

Contains the core data entities for the support system.

**Classes:**

- `Ticket` – Represents a support conversation between a user and support staff.
- `TicketMessage` – Individual message within a ticket.
- `TicketAttachment` – File attached to a specific message.

**Key methods:**

- `Ticket.can_customer_send_message` – Returns `True` if the ticket status allows customer replies.
- `Ticket.can_support_send_message` – Returns `True` if the ticket is waiting for support.
- `TicketMessage.short_preview` – Returns a truncated message preview for admin display.

### `services.py`

Implements the business rules and transaction‑safe operations.

**Functions:**

- `generate_tracking_code()` – Generates a unique 6‑digit numeric code.
- `create_ticket(user, title, subject, message_text, attachments=None)` – Creates a ticket with an initial message.
- `send_customer_message(ticket, user, message_text, attachments=None)` – Sends a customer reply and updates ticket status.
- `send_support_message(ticket, user, message_text, attachments=None)` – Sends a support reply and updates ticket status.
- `close_ticket(ticket)` – Marks a ticket as closed.
- `reopen_ticket(ticket)` – Reopens a closed ticket, setting status to `WAITING_FOR_USER`.

### `views.py`

Customer‑facing views.

**Classes:**

- `TicketListView` – Displays the authenticated user’s tickets (paginated).
- `TicketCreateView` – Handles creation of a new ticket via GET and POST.
- `TicketDetailView` – Shows the conversation and handles customer replies.

### `forms.py`

Defines forms for ticket creation and messaging.

**Classes:**

- `MultipleFileInput` – Custom file input widget allowing multiple file selection.
- `MultipleFileField` – Field that validates multiple files and enforces max 3 attachments.
- `TicketCreateForm` – Form for creating a new ticket (title, subject, message, attachments).
- `TicketMessageForm` – Form for sending a reply (message, attachments).

### `urls.py`

Defines the URL patterns for the support app.

- Registers a custom converter `tracking_code` that matches exactly 6 digits.
- URL patterns: `/`, `/new/`, `/tickets/<tracking_code>/`.

### `validators.py`

Provides secure file validation.

**Constants:**

- Allowed image extensions: `.jpg`, `.jpeg`, `.png`, `.webp`
- Allowed document extension: `.pdf`
- Max image size: 5 MB
- Max document size: 10 MB
- Max attachments per message: 3

**Functions:**

- `get_file_extension(filename)` – Returns lowercase extension.
- `validate_file_size(file, max_size)` – Checks file size limit.
- `validate_image_content(file)` – Uses PIL to verify the file is a valid image.
- `validate_ticket_attachment(file)` – Combined validation (extension, MIME, size, image content); returns category (`image` or `document`).

### `admin.py`

Configures the Django admin interface.

**Classes:**

- `TicketMessageInline` – Tabular inline for messages within a ticket.
- `TicketAttachmentInline` – Tabular inline for attachments within a message.
- `TicketAdmin` – Admin for tickets with custom list display, filters, actions (close/reopen).
- `TicketMessageAdmin` – Admin for messages.
- `TicketAttachmentAdmin` – Admin for attachments.

### `apps.py`

Defines the Django app configuration.

**Class:**

- `SupportConfig` – Sets app name (`apps.support`) and verbose name.

### `tests.py`

Comprehensive unit tests covering:
- Tracking code generation (length, uniqueness)
- Ticket creation
- Authorization (ownership enforcement)
- Message flow (customer‑support turn‑based rules)
- Closed ticket behaviour
- Attachment validation (allowed types, invalid extension, invalid MIME, oversize)

---

## Models

### `Ticket`

| Field | Type | Description |
|-------|------|-------------|
| `user` | `ForeignKey(AUTH_USER_MODEL, on_delete=CASCADE, related_name="support_tickets")` | The customer who owns the ticket. |
| `tracking_code` | `CharField(max_length=6, unique=True)` | Unique 6‑digit tracking code. |
| `title` | `CharField(max_length=200)` | Short ticket title. |
| `subject` | `CharField(max_length=20, choices=Subject.choices)` | Controlled subject category (e.g., ORDER, PAYMENT, …). |
| `status` | `CharField(max_length=20, choices=Status.choices, default=WAITING_FOR_SUPPORT)` | Current ticket state. |
| `created_at` | `DateTimeField(auto_now_add=True)` | Creation timestamp. |
| `updated_at` | `DateTimeField(auto_now=True)` | Last update timestamp. |

**Choices:**

- `Subject`: ORDER, PAYMENT, SHIPPING, PRODUCT, RETURN, ACCOUNT, WEBSITE, OTHER
- `Status`: WAITING_FOR_SUPPORT, WAITING_FOR_USER, CLOSED

### `TicketMessage`

| Field | Type | Description |
|-------|------|-------------|
| `ticket` | `ForeignKey(Ticket, on_delete=CASCADE, related_name="messages")` | The ticket this message belongs to. |
| `sender` | `ForeignKey(AUTH_USER_MODEL, on_delete=CASCADE, related_name="support_messages")` | The user who sent the message. |
| `message` | `TextField` | Message body. |
| `created_at` | `DateTimeField(auto_now_add=True)` | Send timestamp. |
| `updated_at` | `DateTimeField(auto_now=True)` | Last edit timestamp. |

### `TicketAttachment`

| Field | Type | Description |
|-------|------|-------------|
| `message` | `ForeignKey(TicketMessage, on_delete=CASCADE, related_name="attachments")` | The message this file is attached to. |
| `file` | `FileField(upload_to="support/attachments/%Y/%m/")` | The uploaded file. |
| `original_name` | `CharField(max_length=255)` | Original filename before upload. |
| `created_at` | `DateTimeField(auto_now_add=True)` | Upload timestamp. |

---

## Important Business Rules

1. **Turn‑based messaging**:
   - Customer can send only when status is `WAITING_FOR_USER`.
   - Support can send only when status is `WAITING_FOR_SUPPORT`.
   - No messages allowed when status is `CLOSED`.

2. **Ownership enforcement**:
   - Users can only access tickets where `ticket.user == request.user`.
   - All service functions verify ownership before performing actions.

3. **Attachment security**:
   - Only JPG, JPEG, PNG, WEBP, and PDF are allowed.
   - Image files are verified using PIL.
   - Maximum 3 attachments per message.
   - Image max size: 5 MB, PDF max size: 10 MB.

4. **Tracking code**:
   - Generated randomly, 6 digits, unique.
   - Collision handling via database check in a loop.

5. **Transactions**:
   - All multi‑step operations (ticket creation, message sending) are wrapped in `@transaction.atomic` to ensure consistency.

---

## Dependencies / Assumptions

- Uses `Pillow` for image content validation.
- Uses Django’s built‑in authentication (`AUTH_USER_MODEL` from settings).
- Uses PostgreSQL in production, but SQLite is fine for testing.
- Does **not** use `django-taggit` (tags are not part of the support system).

---

## Testing

Run tests with:

```bash
python manage.py test apps.support