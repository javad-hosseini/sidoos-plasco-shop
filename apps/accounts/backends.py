from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()


class CustomAuthenticationBackend(ModelBackend):
    """Authenticate deterministically by username, unique email, or phone."""

    @staticmethod
    def _dummy_password_check(password):
        # Run the default password hasher when no unambiguous user exists.
        UserModel().set_password(password)

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return None

        # Username is unique by Django's AbstractUser contract.
        user = UserModel.objects.filter(username=username).first()

        if user is None:
            # Email is not unique in this project, so never choose arbitrarily.
            email_matches = UserModel.objects.filter(email=username)
            count = email_matches.count()
            if count == 1:
                user = email_matches.first()
            elif count > 1:
                self._dummy_password_check(password)
                return None

        if user is None:
            # phone_number is explicitly unique when present.
            user = UserModel.objects.filter(phone_number=username).first()

        if user is None:
            self._dummy_password_check(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
