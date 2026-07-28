import uuid

from django.conf import settings
from django.db import models

from apps.stores.models import AdvertisingProfile
from apps.tenants.models import Tenant


class AgentTaskStatus(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    RUNNING = "RUNNING", "Running"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"


class AnalysisTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT)
    profile = models.ForeignKey(AdvertisingProfile, on_delete=models.PROTECT)
    status = models.CharField(max_length=16, choices=AgentTaskStatus.choices)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    idempotency_key = models.CharField(max_length=128)
    scope_snapshot = models.JSONField(default=dict)
    result = models.JSONField(default=dict)
    error = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "agent_analysis_task"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "idempotency_key"],
                name="agent_task_tenant_idem_uniq",
            )
        ]


class AgentRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(AnalysisTask, on_delete=models.PROTECT, related_name="runs")
    agent_code = models.CharField(max_length=64)
    schema_version = models.CharField(max_length=16)
    status = models.CharField(max_length=16, choices=AgentTaskStatus.choices)
    output = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agent_run"
        constraints = [
            models.UniqueConstraint(
                fields=["task", "agent_code"], name="agent_run_task_code_uniq"
            )
        ]

