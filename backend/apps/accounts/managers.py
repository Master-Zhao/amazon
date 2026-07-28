from django.contrib.auth.models import UserManager as DjangoUserManager


class UserManager(DjangoUserManager):
    def normalize_email(self, email):
        normalized = super().normalize_email(email)
        return normalized.strip().casefold() if normalized else normalized
