# apps/accounts/apps.py
from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    label = 'accounts'  # This is important for AUTH_USER_MODEL

    def ready(self):
        # Import signals if you have any
        # import apps.accounts.signals
        pass