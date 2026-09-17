"""
Provider abstraction and MeliPayamak REST implementation.

Handles secure communication with the MeliPayamak SMS Gateway without leaking
credentials into logs, exceptions, or templates.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging
import uuid
import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

# Standard MeliPayamak error code descriptions
MELIPAYAMAK_ERROR_MESSAGES = {
    "0": "نام کاربری یا رمز عبور سامانه پیامک اشتباه است.",
    "2": "اعتبار پنل پیامکی کافی نمی‌باشد.",
    "3": "محدودیت در تعداد ارسال روزانه.",
    "4": "محدودیت در حجم ارسال.",
    "5": "شماره فرستنده معتبر نمی‌باشد یا به پنل تعلق ندارد.",
    "6": "سامانه پیامک در حال بروزرسانی می‌باشد.",
    "7": "متن پیامک حاوی کلمات فیلتر شده می‌باشد.",
    "9": "ارسال از خطوط عمومی از طریق وب‌سرویس امکان‌پذیر نمی‌باشد.",
    "10": "حساب کاربری در سامانه پیامک فعال نمی‌باشد.",
    "11": "پیامک ارسال نشد.",
    "12": "مدارک هویتی در سامانه پیامک تایید نشده است.",
    "14": "متن پیامک حاوی لینک غیرمجاز می‌باشد.",
    "15": "ارسال گروهی بدون درج گزینه لغو امکان‌پذیر نیست.",
    "16": "شماره گیرنده‌ای یافت نشد.",
    "17": "متن پیامک خالی می‌باشد.",
    "18": "شماره گیرنده نامعتبر است.",
    "-108": "آدرس IP به دلیل تلاش‌های ناموفق مکرر مسدود شده است.",
    "-109": "الزام به تنظیم آدرس IP مجاز در پنل ملی‌پیامک.",
    "-110": "الزام به استفاده از کلید API (ApiKey) به جای رمز عبور.",
}


@dataclass
class ProviderResult:
    success: bool
    rec_id: str = ""
    error_code: str = ""
    error_message: str = ""
    raw_response: str = ""


class BaseSmsProvider(ABC):
    """Abstract SMS gateway provider interface."""

    @abstractmethod
    def send_simple_sms(
        self,
        recipients: list[str],
        text: str,
        is_flash: bool = False,
    ) -> ProviderResult:
        """
        Send an arbitrary SMS to one or multiple recipients.

        Args:
            recipients: List of normalized 11-digit phone numbers.
            text: SMS body text.
            is_flash: Whether to send as flash SMS.

        Returns:
            ProviderResult: Result structure indicating success or failure.
        """
        pass

    def send_pattern_sms(
        self,
        to: str,
        body_id: int,
        args: list[str],
    ) -> ProviderResult:
        """
        Extensible hook for future Pattern SMS (SendByBaseNumber).
        """
        raise NotImplementedError("ارسال پیامک پترن هنوز در این نسخه فعال نشده است.")


class MeliPayamakRestProvider(BaseSmsProvider):
    """
    Direct HTTP/REST client for MeliPayamak using requests.
    Endpoint: rest.payamak-panel.com/api/SendSMS/SendSMS
    """

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        from_number: str | None = None,
        base_url: str | None = None,
        timeout: int = 15,
    ):
        self.username = username or getattr(settings, "MELIPAYAMAK_USERNAME", "")
        self.password = password or getattr(settings, "MELIPAYAMAK_PASSWORD", "")
        self.from_number = from_number or getattr(settings, "MELIPAYAMAK_FROM_NUMBER", "")
        self.base_url = base_url or getattr(
            settings,
            "MELIPAYAMAK_API_BASE_URL",
            "https://rest.payamak-panel.com/api/SendSMS/SendSMS",
        )
        self.timeout = timeout

        if not self.username or not self.password or not self.from_number:
            raise ImproperlyConfigured(
                "تنظیمات وب‌سرویس ملی‌پیامک (نام کاربری، رمز عبور، شماره خط فرستنده) در فایل تنطیمات تعریف نشده است."
            )

    def send_simple_sms(
        self,
        recipients: list[str],
        text: str,
        is_flash: bool = False,
    ) -> ProviderResult:
        if not recipients:
            return ProviderResult(
                success=False,
                error_code="EMPTY_RECIPIENTS",
                error_message="لیست گیرندگان خالی است.",
            )

        if not text or not text.strip():
            return ProviderResult(
                success=False,
                error_code="EMPTY_TEXT",
                error_message="متن پیامک نمی‌تواند خالی باشد.",
            )

        # MeliPayamak supports comma-separated recipient numbers or individual number
        to_param = ",".join(recipients) if len(recipients) > 1 else recipients[0]

        payload = {
            "username": self.username,
            "password": self.password,
            "to": to_param,
            "from": self.from_number,
            "text": text,
            "isflash": "true" if is_flash else "false",
        }

        try:
            response = requests.post(
                self.base_url,
                data=payload,
                timeout=self.timeout,
                headers={"Cache-Control": "no-cache"},
            )
            response.raise_for_status()
            raw_text = response.text.strip()
            return self._parse_provider_response(raw_text)

        except requests.exceptions.Timeout:
            logger.error("Timeout connecting to MeliPayamak gateway.")
            return ProviderResult(
                success=False,
                error_code="TIMEOUT",
                error_message="مهلت زمانی ارتباط با درگاه ملی‌پیامک به پایان رسید.",
            )
        except requests.exceptions.RequestException as e:
            logger.error("HTTP error connecting to MeliPayamak: %s", type(e).__name__)
            return ProviderResult(
                success=False,
                error_code="HTTP_ERROR",
                error_message="خطای شبکه در ارتباط با سرور پیامک رخ داد.",
            )
        except Exception:
            logger.exception("Unexpected error in MeliPayamakRestProvider")
            return ProviderResult(
                success=False,
                error_code="INTERNAL_ERROR",
                error_message="خطای سیستمی در ارسال پیامک رخ داد.",
            )

    def _parse_provider_response(self, raw_text: str) -> ProviderResult:
        """
        Parses provider response text or JSON.
        Successful sends return a numeric receipt ID (recId, typically > 15).
        Error codes are small integers (0, 2, 3..18) or negative (-108, -109, -110).
        """
        # Try JSON first if provider returns {"Value": "..."} or {"RetStatus": 1}
        value_str = raw_text.strip().strip('"').strip("'")
        if "{" in raw_text and "}" in raw_text:
            try:
                import json
                data = json.loads(raw_text)
                if isinstance(data, dict):
                    if "Value" in data:
                        value_str = str(data["Value"]).strip()
                    elif "StrRetStatus" in data:
                        value_str = str(data["StrRetStatus"]).strip()
                    elif "RetStatus" in data:
                        value_str = str(data["RetStatus"]).strip()
            except Exception:
                pass

        # Handle numeric return values
        try:
            code_num = int(float(value_str))
            # Standard MeliPayamak rule: a receipt ID is a large integer (> 15)
            # Codes <= 15 (except 1) or negative are specific error conditions
            if code_num > 15:
                return ProviderResult(
                    success=True,
                    rec_id=str(code_num),
                    raw_response=raw_text,
                )
            elif code_num == 1:
                return ProviderResult(
                    success=True,
                    rec_id="OK",
                    raw_response=raw_text,
                )
            else:
                err_desc = MELIPAYAMAK_ERROR_MESSAGES.get(
                    str(code_num),
                    f"خطای ناشناخته از درگاه پیامک (کد: {code_num})",
                )
                return ProviderResult(
                    success=False,
                    error_code=str(code_num),
                    error_message=err_desc,
                    raw_response=raw_text,
                )
        except (ValueError, TypeError):
            # Non-numeric response
            if "ok" in value_str.lower() or "success" in value_str.lower():
                return ProviderResult(
                    success=True,
                    rec_id=value_str,
                    raw_response=raw_text,
                )
            return ProviderResult(
                success=False,
                error_code="UNKNOWN_RESPONSE",
                error_message=f"پاسخ ناشناخته از درگاه ملی‌پیامک: {value_str[:100]}",
                raw_response=raw_text,
            )


class ConsoleSmsProvider(BaseSmsProvider):
    """
    Mock SMS provider that logs outgoing SMS to console/logger without contacting external APIs.
    Used for local development and testing to prevent external network side effects and billing.
    """

    def send_simple_sms(
        self,
        recipients: list[str],
        text: str,
        is_flash: bool = False,
    ) -> ProviderResult:
        mock_rec_id = f"MOCK-{uuid.uuid4().hex[:8].upper()}"
        logger.info(
            "[CONSOLE SMS] Sent to %d recipient(s): %s | RecId: %s | Text: %s",
            len(recipients),
            recipients[:5] if len(recipients) > 5 else recipients,
            mock_rec_id,
            text[:100] + ("..." if len(text) > 100 else ""),
        )
        return ProviderResult(
            success=True,
            rec_id=mock_rec_id,
            raw_response=f"Console mock send to {len(recipients)} numbers",
        )


def get_sms_provider() -> BaseSmsProvider:
    """
    Factory function to obtain the active SMS provider instance.
    Falls back to ConsoleSmsProvider if SMS_CONSOLE_MODE is True or credentials are empty.
    """
    is_console = getattr(settings, "SMS_CONSOLE_MODE", False)
    username = getattr(settings, "MELIPAYAMAK_USERNAME", "")
    password = getattr(settings, "MELIPAYAMAK_PASSWORD", "")
    from_number = getattr(settings, "MELIPAYAMAK_FROM_NUMBER", "")

    if is_console or not (username and password and from_number):
        if not is_console:
            logger.warning(
                "MeliPayamak credentials are not fully configured. Falling back to ConsoleSmsProvider."
            )
        return ConsoleSmsProvider()

    return MeliPayamakRestProvider()

