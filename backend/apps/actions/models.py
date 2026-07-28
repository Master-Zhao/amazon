from django.conf import settings
from django.db import models

from apps.core.models import AppendOnlyModel
from apps.recommendations.models import RecommendationRevision
from apps.stores.models import AdvertisingProfile
from apps.tenants.models import Tenant


class ActionPreviewStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PENDING_APPROVAL = "PENDING_APPROVAL", "Pending approval"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    RETURNED = "RETURNED", "Returned"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"


class ApprovalDecision(models.TextChoices):
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    RETURNED = "RETURNED", "Returned"


class ExecutionOutcome(models.TextChoices):
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    SUCCESS = "SUCCESS", "Success (legacy)"
    FAILED = "FAILED", "Failed"
    SKIPPED = "SKIPPED", "Skipped"


class ActionPreview(models.Model):
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="action_previews",
    )
    profile = models.ForeignKey(
        AdvertisingProfile,
        on_delete=models.PROTECT,
        related_name="action_previews",
    )
    recommendation_revision = models.ForeignKey(
        RecommendationRevision,
        on_delete=models.PROTECT,
        related_name="action_previews",
    )
    status = models.CharField(
        max_length=32,
        choices=ActionPreviewStatus.choices,
        default=ActionPreviewStatus.DRAFT,
    )
    current_version_number = models.PositiveIntegerField(default=1)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="submitted_action_previews",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_action_previews",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "action_preview"
        constraints = [
            models.UniqueConstraint(
                fields=["recommendation_revision", "created_by"],
                name="action_preview_revision_creator_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["tenant", "profile", "status", "-created_at"],
                name="action_prev_scope_status_idx",
            )
        ]


class ActionPreviewVersion(AppendOnlyModel):
    preview = models.ForeignKey(
        ActionPreview,
        on_delete=models.PROTECT,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField()
    action_payload = models.JSONField()
    object_state_version = models.CharField(max_length=128)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="action_preview_versions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "action_preview_version"
        constraints = [
            models.UniqueConstraint(
                fields=["preview", "version_number"],
                name="action_preview_version_uniq",
            )
        ]


class ApprovalRecord(AppendOnlyModel):
    preview = models.ForeignKey(
        ActionPreview,
        on_delete=models.PROTECT,
        related_name="approval_records",
    )
    preview_version = models.ForeignKey(
        ActionPreviewVersion,
        on_delete=models.PROTECT,
        related_name="approval_records",
    )
    decision = models.CharField(max_length=16, choices=ApprovalDecision.choices)
    comment = models.CharField(max_length=1000, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approval_records",
    )
    idempotency_key = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "action_approval_record"


class ExecutionRecord(AppendOnlyModel):
    preview = models.ForeignKey(
        ActionPreview,
        on_delete=models.PROTECT,
        related_name="execution_records",
    )
    preview_version = models.ForeignKey(
        ActionPreviewVersion,
        on_delete=models.PROTECT,
        related_name="execution_records",
    )
    outcome = models.CharField(max_length=16, choices=ExecutionOutcome.choices)
    actual_value = models.JSONField(default=dict)
    executed_at = models.DateTimeField()
    note = models.CharField(max_length=1000, blank=True)
    evidence_metadata = models.JSONField(default=dict)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="execution_records",
    )
    idempotency_key = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "action_execution_record"
        constraints = [
            models.UniqueConstraint(
                fields=["preview", "preview_version"],
                name="action_execution_preview_version_uniq",
            )
        ]


class EffectEvaluation(AppendOnlyModel):
    execution_record = models.ForeignKey(
        ExecutionRecord,
        on_delete=models.PROTECT,
        related_name="effect_evaluations",
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="effect_evaluations",
    )
    profile = models.ForeignKey(
        AdvertisingProfile,
        on_delete=models.PROTECT,
        related_name="effect_evaluations",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="effect_evaluations",
    )
    status = models.CharField(max_length=32)
    baseline_start = models.DateField()
    baseline_end = models.DateField()
    observation_start = models.DateField()
    observation_end = models.DateField()
    celery_task_id = models.CharField(max_length=128, unique=True)
    idempotency_key = models.CharField(max_length=128, unique=True)
    result = models.JSONField(default=dict)
    reason_code = models.CharField(max_length=96, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "action_effect_evaluation"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "execution_record",
                    "baseline_start",
                    "baseline_end",
                    "observation_start",
                    "observation_end",
                ],
                name="action_effect_window_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["tenant", "profile", "status", "created_at"],
                name="action_effect_scope_status_idx",
            )
        ]
