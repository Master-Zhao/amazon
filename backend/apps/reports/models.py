from django.conf import settings
from django.db import models

from apps.core.models import AppendOnlyModel
from apps.stores.models import AdvertisingProfile
from apps.tenants.models import Tenant


class ReportType(models.TextChoices):
    CAMPAIGN = "CAMPAIGN", "Campaign"
    TARGETING = "TARGETING", "Targeting"
    SEARCH_TERM = "SEARCH_TERM", "Search term"


class ReportSourceType(models.TextChoices):
    FILE_UPLOAD = "FILE_UPLOAD", "File upload"
    THIRD_PARTY = "THIRD_PARTY", "Third party"
    AMAZON_ADS_API = "AMAZON_ADS_API", "Amazon Ads API"


class ImportTaskStatus(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    RUNNING = "RUNNING", "Running"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    PARTIAL_SUCCEEDED = "PARTIAL_SUCCEEDED", "Partially succeeded"
    FAILED = "FAILED", "Failed"


class ReportUpload(AppendOnlyModel):
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="report_uploads",
    )
    profile = models.ForeignKey(
        AdvertisingProfile,
        on_delete=models.PROTECT,
        related_name="report_uploads",
    )
    report_type = models.CharField(max_length=32, choices=ReportType.choices)
    source_type = models.CharField(
        max_length=32,
        choices=ReportSourceType.choices,
        default=ReportSourceType.FILE_UPLOAD,
    )
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=128, blank=True)
    size_bytes = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    storage_key = models.CharField(max_length=500)
    duplicate_of = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="duplicates",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="report_uploads",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "report_upload"
        indexes = [
            models.Index(
                fields=["tenant", "profile", "report_type", "-created_at"],
                name="report_up_scope_created_idx",
            ),
            models.Index(
                fields=["tenant", "sha256"],
                name="report_upload_tenant_hash_idx",
            ),
        ]


class ImportTask(models.Model):
    upload = models.ForeignKey(
        ReportUpload,
        on_delete=models.PROTECT,
        related_name="import_tasks",
    )
    status = models.CharField(
        max_length=32,
        choices=ImportTaskStatus.choices,
        default=ImportTaskStatus.QUEUED,
    )
    celery_task_id = models.CharField(max_length=128, blank=True)
    total_rows = models.PositiveIntegerField(default=0)
    success_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    error_code = models.CharField(max_length=96, blank=True)
    error_message = models.TextField(blank=True)
    reprocessed_from = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reprocess_attempts",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="report_import_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "report_import_task"
        indexes = [
            models.Index(
                fields=["status", "created_at"],
                name="report_task_status_created_idx",
            )
        ]


class ImportBatch(models.Model):
    task = models.OneToOneField(
        ImportTask,
        on_delete=models.PROTECT,
        related_name="batch",
    )
    schema_version = models.CharField(max_length=32)
    idempotency_key = models.CharField(max_length=128, unique=True)
    normalized_storage_key = models.CharField(max_length=500, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "report_import_batch"


class ImportRowError(AppendOnlyModel):
    task = models.ForeignKey(
        ImportTask,
        on_delete=models.PROTECT,
        related_name="row_errors",
    )
    row_number = models.PositiveIntegerField()
    error_code = models.CharField(max_length=96)
    message = models.CharField(max_length=1000)
    field_name = models.CharField(max_length=128, blank=True)
    rejected_value = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "report_import_row_error"
        indexes = [
            models.Index(
                fields=["task", "row_number"],
                name="report_row_error_task_row_idx",
            )
        ]
