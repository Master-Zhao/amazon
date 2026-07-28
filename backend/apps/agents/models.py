from django.conf import settings
from django.db import models

from apps.stores.models import AdvertisingProfile
from apps.tenants.models import Tenant


class AgentCode(models.TextChoices):
    DATA_ANALYSIS = "DATA_ANALYSIS", "Data analysis"
    ANOMALY_DIAGNOSIS = "ANOMALY_DIAGNOSIS", "Anomaly diagnosis"
    BUDGET_ANALYSIS = "BUDGET_ANALYSIS", "Budget analysis"
    COMPOSITE_STRATEGY = "COMPOSITE_STRATEGY", "Composite strategy"


class AgentRunStatus(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    RUNNING = "RUNNING", "Running"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"


class AgentRun(models.Model):
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="agent_runs",
    )
    profile = models.ForeignKey(
        AdvertisingProfile,
        on_delete=models.PROTECT,
        related_name="agent_runs",
    )
    agent_code = models.CharField(
        max_length=32,
        choices=AgentCode.choices,
        default=AgentCode.COMPOSITE_STRATEGY,
    )
    status = models.CharField(
        max_length=16,
        choices=AgentRunStatus.choices,
        default=AgentRunStatus.QUEUED,
    )
    schema_version = models.CharField(max_length=32, default="agent-result-v1")
    celery_task_id = models.CharField(max_length=128)
    input_snapshot = models.JSONField(default=dict)
    output_result = models.JSONField(default=dict)
    error_code = models.CharField(max_length=96, blank=True)
    error_message = models.TextField(blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="agent_runs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "agent_run"
        indexes = [
            models.Index(
                fields=["tenant", "profile", "-created_at"],
                name="agent_run_scope_created_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="agent_run_status_created_idx",
            ),
        ]
