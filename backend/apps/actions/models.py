import uuid

from django.conf import settings
from django.db import models

from apps.recommendations.models import Recommendation
from apps.stores.models import AdvertisingProfile
from apps.tenants.models import Tenant


class PreviewStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PENDING_APPROVAL = "PENDING_APPROVAL", "Pending approval"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    RETURNED = "RETURNED", "Returned"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"


class ActionPreview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT)
    profile = models.ForeignKey(AdvertisingProfile, on_delete=models.PROTECT)
    status = models.CharField(
        max_length=32, choices=PreviewStatus.choices, default=PreviewStatus.DRAFT
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    current_version = models.PositiveIntegerField(default=1)
    version_lock = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "action_preview"


class ActionPreviewVersion(models.Model):
    preview = models.ForeignKey(
        ActionPreview, on_delete=models.PROTECT, related_name="versions"
    )
    version = models.PositiveIntegerField()
    items = models.JSONField()
    content_hash = models.CharField(max_length=64)
    frozen_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "action_preview_version"
        constraints = [
            models.UniqueConstraint(
                fields=["preview", "version"], name="action_preview_version_uniq"
            )
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self).objects.only("frozen_at").get(pk=self.pk)
            if original.frozen_at is not None:
                raise RuntimeError("Frozen action preview versions are immutable")
        return super().save(*args, **kwargs)


class ApprovalRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    preview = models.ForeignKey(
        ActionPreview, on_delete=models.PROTECT, related_name="approvals"
    )
    version = models.ForeignKey(ActionPreviewVersion, on_delete=models.PROTECT)
    decision = models.CharField(max_length=32)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    comment = models.CharField(max_length=500, blank=True)
    idempotency_key = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "action_approval_record"
        constraints = [
            models.UniqueConstraint(
                fields=["preview", "idempotency_key"],
                name="action_approval_idem_uniq",
            )
        ]


class ExecutionTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    preview = models.OneToOneField(
        ActionPreview, on_delete=models.PROTECT, related_name="execution_task"
    )
    version = models.ForeignKey(ActionPreviewVersion, on_delete=models.PROTECT)
    status = models.CharField(max_length=32, default="WAITING_CONFIRMATION")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "action_execution_task"


class ExecutionItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(ExecutionTask, on_delete=models.PROTECT, related_name="items")
    item_index = models.PositiveIntegerField()
    action = models.JSONField()
    status = models.CharField(max_length=16, default="PENDING")

    class Meta:
        db_table = "action_execution_item"
        constraints = [
            models.UniqueConstraint(
                fields=["task", "item_index"], name="action_execution_item_uniq"
            )
        ]


class ExecutionRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(
        ExecutionItem, on_delete=models.PROTECT, related_name="records"
    )
    result = models.CharField(max_length=16)
    actual_value = models.JSONField(default=dict)
    executed_at = models.DateTimeField()
    note = models.CharField(max_length=500, blank=True)
    evidence_path = models.CharField(max_length=500, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    idempotency_key = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "action_execution_record"
        constraints = [
            models.UniqueConstraint(
                fields=["item", "idempotency_key"],
                name="action_execution_record_idem_uniq",
            )
        ]


class EffectEvaluation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    execution_task = models.ForeignKey(
        ExecutionTask, on_delete=models.PROTECT, related_name="evaluations"
    )
    status = models.CharField(max_length=16)
    baseline = models.JSONField(default=dict)
    observed = models.JSONField(default=dict)
    evaluated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "action_effect_evaluation"
