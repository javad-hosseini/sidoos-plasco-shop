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
