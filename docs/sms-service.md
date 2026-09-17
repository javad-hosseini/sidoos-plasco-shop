# SMS Management Service (MeliPayamak)

Complete technical documentation for the SMS module is located in the app directory:
👉 **[apps/sms_service/README.md](file:///d:/projects/websites/sidoos-plasco-shop/apps/sms_service/README.md)**

### Summary of Key Features
- **Provider**: Direct MeliPayamak REST API via `requests` (no SOAP/zeep dependency).
- **Recipients**:
  - Registered website users (`accounts.User`) with personalized greeting: `{full_name} عزیز\n{message}` (fallback: `کاربر گرامی`).
  - Contact book entries (`Contact`) with raw text without greeting.
- **Cross-Deduplication**: Numbers belonging to both sources are deduplicated, with Registered Users taking precedence.
- **Batching & Concurrency**:
  - Registered users: executed concurrently using `ThreadPoolExecutor` (5 workers).
  - Contacts: chunked into batches of 100 per MeliPayamak Simple SMS specification.
- **Audit Logging**: `SmsCampaign` (summary) and `SmsRecipientLog` (per-recipient status, recId, error code).
- **Admin Workflow**: Interactive Send SMS Center in Jazzmin Admin with search, live counters, live preview, and safety confirmation step.
- **CLI Diagnostics**: `python manage.py send_test_sms 0912xxxxxxx [--real]`
- **Testing**: 39 comprehensive unit tests with zero real SMS sent during tests.

