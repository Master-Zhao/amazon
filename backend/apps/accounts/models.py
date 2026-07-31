from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from apps.accounts.managers import UserManager


class User(AbstractUser):
    email = models.EmailField("email address", unique=True)
    objects = UserManager()

    def clean(self):
        super().clean()
        self.email = type(self).objects.normalize_email(self.email)

    def save(self, *args, **kwargs):
        self.email = type(self).objects.normalize_email(self.email)
        return super().save(*args, **kwargs)

    class Meta:
        db_table = "sys_user"
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="sys_user_email_ci_uniq",
            )
        ]


class ExternalIdentitySource(models.TextChoices):
    SCM_MERCHANT_ADMIN = "SCM_MERCHANT_ADMIN", "SCM Merchant Admin"


class ExternalIdentity(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="external_identities",
    )
    source = models.CharField(
        max_length=32,
        choices=ExternalIdentitySource.choices,
    )
    external_user_id = models.CharField(max_length=128)
    external_merchant_id = models.CharField(max_length=128)
    identifier = models.CharField(max_length=254)
    last_authenticated_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sys_external_identity"
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_user_id"],
                name="sys_external_identity_user_uniq",
            ),
            models.UniqueConstraint(
                fields=["source", "identifier"],
                name="sys_external_identity_name_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "source"],
                name="sys_external_user_source_idx",
            )
        ]


class RefreshTokenRecord(models.Model):
    token_hash = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="refresh_token_records",
    )
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    rotated_to = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        db_table = "sys_refresh_token"
        indexes = [
            models.Index(
                fields=["user", "expires_at"],
                name="sys_refresh_user_exp_idx",
            )
        ]


class AuthenticationAuditEvent(models.Model):
    event = models.CharField(max_length=32)
    outcome = models.CharField(max_length=32)
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    email_hash = models.CharField(max_length=64, blank=True)
    request_id = models.CharField(max_length=128)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_auth_event"
        indexes = [
            models.Index(
                fields=["event", "created_at"],
                name="audit_auth_event_time_idx",
            )
        ]
