import uuid

from django.conf import settings
from django.db import models

from apps.tenants.models import Tenant


class AppendOnlyQuerySet(models.QuerySet):
    def delete(self):
        raise RuntimeError("AuditLog is append-only")


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, null=True, on_delete=models.PROTECT)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT
    )
    event = models.CharField(max_length=64)
    object_type = models.CharField(max_length=64)
    object_id = models.CharField(max_length=128)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    request_id = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "audit_log"
        indexes = [
            models.Index(fields=["tenant", "created_at"], name="audit_tenant_time_idx")
        ]

    def delete(self, *args, **kwargs):
        raise RuntimeError("AuditLog is append-only")
