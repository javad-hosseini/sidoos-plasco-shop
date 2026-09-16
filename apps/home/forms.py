"""
Forms for the home application.
"""

from django import forms


class NewsletterSubscriptionForm(forms.Form):
    """Validates an email submitted through the homepage newsletter form."""

    email = forms.EmailField(
        label="ایمیل",
        error_messages={
            "required": "لطفاً ایمیل خود را وارد کنید.",
            "invalid": "لطفاً یک ایمیل معتبر وارد کنید.",
        },
    )


from .models import ContactMessage


class ContactForm(forms.ModelForm):
    """Validates and processes public contact inquiries submitted at /contact/."""

    class Meta:
        model = ContactMessage
        fields = ["name", "phone", "subject", "message"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "مثال: علی رضایی",
                    "required": True,
                    "id": "contact_name",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "dir": "ltr",
                    "placeholder": "۰۹۱۲۳۴۵۶۷۸۹",
                    "required": True,
                    "id": "contact_phone",
                }
            ),
            "subject": forms.Select(
                attrs={
                    "class": "form-control",
                    "id": "contact_subject",
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "پیام خود را بنویسید...",
                    "required": True,
                    "id": "contact_message",
                    "rows": 4,
                }
            ),
        }
        error_messages = {
            "name": {
                "required": "لطفاً نام و نام خانوادگی خود را وارد کنید.",
                "max_length": "نام وارد شده بیش از حد مجاز است.",
            },
            "phone": {
                "required": "لطفاً شماره تماس خود را وارد کنید.",
            },
            "message": {
                "required": "لطفاً متن پیام خود را بنویسید.",
            },
        }

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        persian_digits = "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩"
        english_digits = "01234567890123456789"
        translation_table = str.maketrans(persian_digits, english_digits)
        phone = phone.translate(translation_table)
        clean = "".join(c for c in phone if c.isdigit() or c == "+")
        if len(clean) < 7:
            raise forms.ValidationError("لطفاً یک شماره تماس معتبر وارد فرمایید.")
        return clean

