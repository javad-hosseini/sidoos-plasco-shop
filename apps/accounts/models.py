from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)

    #Set to true as all registered Users should have this option as of now, this variable is mainly for future scaling purposes
    has_price_access = models.BooleanField(default=True)

    def __str__(self):
        return self.username