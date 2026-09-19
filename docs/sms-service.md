# SMS Management Service (MeliPayamak)

Complete technical documentation for the SMS module is located in the app directory:
👉 **[apps/sms_service/README.md](file:///d:/projects/websites/sidoos-plasco-shop/apps/sms_service/README.md)**

### Summary of Key Features
- **Provider**: Token-based MeliPayamak Simple SMS Console API (`https://console.melipayamak.com/api/send/simple/{token}`) via `requests` (no SOAP/zeep dependency).
- **Authentication**: `MELIPAYAMAK_API_TOKEN` and `MELIPAYAMAK_SENDER` managed through environment variables without hardcoded secrets.
- **Recipients**:
  - Registered website users (`accounts.User`) with personalized greeting: `{full_name} عزیز\n{message}` (fallback: `کاربر گرامی`).
  - Contact book entries (`Contact`) with raw text without greeting.
- **Cross-Deduplication**: Numbers belonging to both sources are deduplicated, with Registered Users taking precedence.
- **Concurrency & Dispatch**:
  - Registered users and contacts are dispatched concurrently using `ThreadPoolExecutor` (up to 5 workers).
  - Clean audit trail recording each recipient's specific `recId` and provider `status`.
- **Audit Logging**: `SmsCampaign` (summary) and `SmsRecipientLog` (per-recipient status, recId, error code).
- **Admin Workflow**: Interactive Send SMS Center in Jazzmin Admin with search, live counters, live preview, and safety confirmation step.
- **CLI Diagnostics**: `python manage.py send_test_sms 0912xxxxxxx [--real]`
- **Testing**: 45 comprehensive unit tests with zero real SMS sent during tests and full mock coverage.
