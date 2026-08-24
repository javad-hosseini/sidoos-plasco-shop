from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

UserModel = get_user_model()

class CustomAuthenticationBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)

        try:
            # Look up the user by username, email, or phone_number
            user = UserModel.objects.get(
                Q(username=username) |
                Q(email=username) |
                Q(phone_number=username)
            )
        except UserModel.DoesNotExist:
            # Run the default password hasher to reduce timing attacks
            UserModel().set_password(password)
            return None
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None