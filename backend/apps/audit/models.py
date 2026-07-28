from django.conf import settings
from django.db import models

from apps.tenants.models import Tenant


class AuditLog(models.Model):
    tenant = models.ForeignKey(
        Tenant,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    event = models.CharField(max_length=96)
    object_type = models.CharField(max_length=96, blank=True)
    object_id = models.CharField(max_length=128, blank=True)
    request_id = models.CharField(max_length=128)
    task_id = models.CharField(max_length=128, blank=True)
    before_data = models.JSONField(default=dict)
    after_data = models.JSONField(default=dict)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise TypeError("AuditLog is append-only")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("AuditLog is append-only")

    class Meta:
        db_table = "audit_log"
        indexes = [
            models.Index(
                fields=["tenant", "-created_at"],
                name="audit_tenant_created_idx",
            ),
            models.Index(
                fields=["event", "-created_at"],
                name="audit_event_created_idx",
            ),
        ]
