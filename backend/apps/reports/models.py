import uuid

from django.conf import settings
from django.db import models

from apps.stores.models import AdvertisingProfile
from apps.tenants.models import Tenant


class ReportType(models.TextChoices):
    CAMPAIGN = "CAMPAIGN", "Campaign"
    TARGETING = "TARGETING", "Targeting"
    SEARCH_TERM = "SEARCH_TERM", "Search Term"


class ImportStatus(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    RUNNING = "RUNNING", "Running"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    PARTIAL_SUCCEEDED = "PARTIAL_SUCCEEDED", "Partial succeeded"
    FAILED = "FAILED", "Failed"


class ReportUpload(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT)
    profile = models.ForeignKey(AdvertisingProfile, on_delete=models.PROTECT)
    report_type = models.CharField(max_length=32, choices=ReportType.choices)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=128)
    size_bytes = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    storage_path = models.CharField(max_length=500)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_duplicate = models.BooleanField(default=False)

    class Meta:
        db_table = "report_upload"
        indexes = [
            models.Index(
                fields=["profile", "report_type", "sha256"],
                name="report_upload_duplicate_idx",
            )
        ]


class ImportTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    upload = models.ForeignKey(ReportUpload, on_delete=models.PROTECT, related_name="tasks")
    status = models.CharField(max_length=32, choices=ImportStatus.choices)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    idempotency_key = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "report_import_task"
        constraints = [
            models.UniqueConstraint(
                fields=["upload", "idempotency_key"],
                name="report_task_upload_idempotency_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["status", "created_at"], name="report_task_status_time_idx")
        ]


class ImportBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.OneToOneField(ImportTask, on_delete=models.PROTECT, related_name="batch")
    status = models.CharField(max_length=32, choices=ImportStatus.choices)
    total_rows = models.PositiveIntegerField(default=0)
    succeeded_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)
    normalized_rows_path = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "report_import_batch"


class ImportRowError(models.Model):
    batch = models.ForeignKey(ImportBatch, on_delete=models.PROTECT, related_name="row_errors")
    row_number = models.PositiveIntegerField()
    code = models.CharField(max_length=64)
    field = models.CharField(max_length=128, blank=True)
    message = models.CharField(max_length=500)
    raw_excerpt = models.JSONField(default=dict)

    class Meta:
        db_table = "report_import_row_error"
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "row_number", "code", "field"],
                name="report_row_error_uniq",
            )
        ]

