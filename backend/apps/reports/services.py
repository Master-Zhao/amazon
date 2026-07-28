import gzip
import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound
from rest_framework.serializers import ValidationError

from apps.advertising.services import (
    upsert_campaign_report_entities,
    upsert_search_term_report_entities,
    upsert_targeting_report_entities,
)
from apps.audit.services import append_audit_log
from apps.permissions.models import ProfileAccessLevel
from apps.permissions.services import require_profile_scope
from apps.reports.models import (
    ImportBatch,
    ImportRowError,
    ImportTask,
    ImportTaskStatus,
    ReportSourceType,
    ReportType,
    ReportUpload,
)
from apps.reports.parsers import (
    ReportStructureError,
    iter_report_rows,
    normalize_report_row,
    schema_version_for,
)
from integrations.advertising_data.sources import FileUploadReportSource
from integrations.storage.local import LocalFileStorage


@dataclass(frozen=True, slots=True)
class SystemRequest:
    request_id: str


def _safe_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise ValidationError(
            {"file": ["Only CSV and XLSX report files are accepted."]}
        )
    return suffix


def _validate_upload_signature(*, uploaded_file, suffix: str) -> None:
    content_type = (uploaded_file.content_type or "").split(";", 1)[0].lower()
    allowed_types = {
        ".csv": {
            "",
            "application/csv",
            "application/octet-stream",
            "application/vnd.ms-excel",
            "text/csv",
            "text/plain",
        },
        ".xlsx": {
            "",
            "application/octet-stream",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/zip",
        },
    }
    if content_type not in allowed_types[suffix]:
        raise ValidationError(
            {"file": ["The content type does not match the report extension."]}
        )
    header = uploaded_file.read(4096)
    uploaded_file.seek(0)
    if suffix == ".xlsx" and not header.startswith(b"PK\x03\x04"):
        raise ValidationError({"file": ["The XLSX file signature is invalid."]})
    if suffix == ".csv" and b"\x00" in header:
        raise ValidationError({"file": ["The CSV file contains binary data."]})


@transaction.atomic
def create_report_import(
    *,
    request,
    tenant_id,
    profile_id,
    report_type: str,
    uploaded_file,
) -> ImportTask:
    if report_type not in ReportType.values:
        raise ValidationError({"report_type": ["Unsupported report type."]})
    scope = require_profile_scope(
        user=request.user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="reports.upload",
        minimum_level=ProfileAccessLevel.OPERATE,
    )
    suffix = _safe_extension(uploaded_file.name)
    _validate_upload_signature(uploaded_file=uploaded_file, suffix=suffix)
    declared_size = int(uploaded_file.size or 0)
    if declared_size <= 0:
        raise ValidationError({"file": ["The report file is empty."]})
    if declared_size > settings.REPORT_MAX_UPLOAD_BYTES:
        raise ValidationError({"file": ["The report exceeds the upload size limit."]})

    storage = LocalFileStorage()
    storage_key = (
        f"{scope.membership.tenant_id}/{scope.profile.pk}/"
        f"{timezone.now():%Y/%m/%d}/{uuid.uuid4().hex}{suffix}"
    )
    digest = hashlib.sha256()
    observed_size = 0

    def checked_chunks():
        nonlocal observed_size
        for chunk in uploaded_file.chunks():
            observed_size += len(chunk)
            if observed_size > settings.REPORT_MAX_UPLOAD_BYTES:
                raise ValidationError(
                    {"file": ["The report exceeds the upload size limit."]}
                )
            digest.update(chunk)
            yield chunk

    try:
        storage.save(key=storage_key, chunks=checked_chunks())
    except Exception:
        storage.delete(key=storage_key)
        raise

    sha256 = digest.hexdigest()
    duplicate = (
        ReportUpload.objects.filter(
            tenant=scope.membership.tenant,
            profile=scope.profile,
            report_type=report_type,
            sha256=sha256,
        )
        .order_by("created_at")
        .first()
    )
    upload = ReportUpload.objects.create(
        tenant=scope.membership.tenant,
        profile=scope.profile,
        report_type=report_type,
        source_type=ReportSourceType.FILE_UPLOAD,
        original_filename=Path(uploaded_file.name).name,
        content_type=uploaded_file.content_type or "",
        size_bytes=observed_size,
        sha256=sha256,
        storage_key=storage_key,
        duplicate_of=duplicate,
        uploaded_by=request.user,
    )
    celery_task_id = uuid.uuid4().hex
    task = ImportTask.objects.create(
        upload=upload,
        created_by=request.user,
        celery_task_id=celery_task_id,
    )
    append_audit_log(
        request=request,
        tenant=scope.membership.tenant,
        actor=request.user,
        event="report.uploaded",
        object_type="ReportUpload",
        object_id=upload.pk,
        task_id=str(task.pk),
        after_data={
            "profile_id": str(scope.profile.pk),
            "report_type": report_type,
            "filename": upload.original_filename,
            "size_bytes": observed_size,
            "sha256": sha256,
            "duplicate_of": str(duplicate.pk) if duplicate else "",
        },
    )

    from apps.reports.tasks import process_import_task

    transaction.on_commit(
        lambda: process_import_task.apply_async(
            args=[task.pk],
            task_id=celery_task_id,
        )
    )
    return task


def _failure(
    *,
    task_id: int,
    code: str,
    message: str,
) -> ImportTask:
    with transaction.atomic():
        task = (
            ImportTask.objects.select_for_update()
            .select_related("upload__tenant", "created_by")
            .get(pk=task_id)
        )
        task.status = ImportTaskStatus.FAILED
        task.error_code = code
        task.error_message = message[:2000]
        task.finished_at = timezone.now()
        task.save(
            update_fields=[
                "status",
                "error_code",
                "error_message",
                "finished_at",
            ]
        )
        append_audit_log(
            request=SystemRequest(request_id=f"import-task-{task.pk}"),
            tenant=task.upload.tenant,
            actor=task.created_by,
            event="report.import_failed",
            object_type="ImportTask",
            object_id=task.pk,
            task_id=str(task.pk),
            after_data={"error_code": code, "error_message": message[:500]},
        )
        return task


def process_report_import(*, task_id: int) -> ImportTask:
    with transaction.atomic():
        task = (
            ImportTask.objects.select_for_update()
            .select_related(
                "upload__tenant",
                "upload__profile",
                "created_by",
            )
            .get(pk=task_id)
        )
        if task.status in {
            ImportTaskStatus.SUCCEEDED,
            ImportTaskStatus.PARTIAL_SUCCEEDED,
        }:
            return task
        if task.status == ImportTaskStatus.RUNNING:
            return task
        task.status = ImportTaskStatus.RUNNING
        task.started_at = timezone.now()
        task.error_code = ""
        task.error_message = ""
        task.save(
            update_fields=[
                "status",
                "started_at",
                "error_code",
                "error_message",
            ]
        )

    upload = task.upload
    source = FileUploadReportSource(
        storage=LocalFileStorage(),
        storage_key=upload.storage_key,
    )
    normalized_rows: list[dict[str, object]] = []
    row_errors: list[ImportRowError] = []
    total_rows = 0
    try:
        with source.open() as stream:
            for parsed in iter_report_rows(
                stream=stream,
                filename=upload.original_filename,
                report_type=upload.report_type,
            ):
                total_rows += 1
                try:
                    normalized_rows.append(
                        normalize_report_row(
                            parsed,
                            report_type=upload.report_type,
                            expected_profile_id=upload.profile.external_profile_id,
                            expected_currency=upload.profile.currency_code,
                        )
                    )
                except ValueError as exc:
                    message = str(exc)
                    field_name = message.split(" ", 1)[0] if " " in message else ""
                    row_errors.append(
                        ImportRowError(
                            task_id=task.pk,
                            row_number=parsed.row_number,
                            error_code="ROW_VALIDATION_ERROR",
                            message=message,
                            field_name=field_name[:128],
                            rejected_value="",
                        )
                    )
    except ReportStructureError as exc:
        return _failure(
            task_id=task.pk,
            code="REPORT_STRUCTURE_ERROR",
            message=str(exc),
        )
    except (OSError, UnicodeError, ValueError) as exc:
        return _failure(
            task_id=task.pk,
            code="REPORT_READ_ERROR",
            message=str(exc),
        )

    if total_rows == 0:
        return _failure(
            task_id=task.pk,
            code="REPORT_EMPTY",
            message="The report contains no data rows.",
        )
    if not normalized_rows:
        with transaction.atomic():
            ImportRowError.objects.bulk_create(row_errors)
            task = ImportTask.objects.select_for_update().get(pk=task.pk)
            task.total_rows = total_rows
            task.error_rows = len(row_errors)
            task.status = ImportTaskStatus.FAILED
            task.error_code = "ALL_ROWS_INVALID"
            task.error_message = "All report rows failed validation."
            task.finished_at = timezone.now()
            task.save(
                update_fields=[
                    "total_rows",
                    "error_rows",
                    "status",
                    "error_code",
                    "error_message",
                    "finished_at",
                ]
            )
        return task

    payload = gzip.compress(
        b"".join(
            (
                json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode(
                    "utf-8"
                )
                + b"\n"
            )
            for row in normalized_rows
        )
    )
    normalized_key = (
        f"{upload.tenant_id}/{upload.profile_id}/normalized/"
        f"{uuid.uuid4().hex}.jsonl.gz"
    )
    LocalFileStorage().save(key=normalized_key, chunks=[payload])

    with transaction.atomic():
        locked = (
            ImportTask.objects.select_for_update()
            .select_related("upload__tenant", "upload__profile", "created_by")
            .get(pk=task.pk)
        )
        batch = ImportBatch.objects.create(
            task=locked,
            schema_version=schema_version_for(upload.report_type),
            idempotency_key=f"{upload.sha256}:{upload.profile_id}:{task.pk}",
            normalized_storage_key=normalized_key,
            row_count=len(normalized_rows),
        )
        from apps.analytics.services import (
            publish_campaign_metrics,
            publish_search_term_metrics,
            publish_targeting_metrics,
        )

        if upload.report_type == ReportType.CAMPAIGN:
            upsert_campaign_report_entities(batch=batch, rows=normalized_rows)
            published_metrics = publish_campaign_metrics(
                batch=batch,
                rows=normalized_rows,
            )
        elif upload.report_type == ReportType.TARGETING:
            upsert_targeting_report_entities(batch=batch, rows=normalized_rows)
            published_metrics = publish_targeting_metrics(
                batch=batch,
                rows=normalized_rows,
            )
        else:
            upsert_search_term_report_entities(batch=batch, rows=normalized_rows)
            published_metrics = publish_search_term_metrics(
                batch=batch,
                rows=normalized_rows,
            )
        if row_errors:
            ImportRowError.objects.bulk_create(row_errors)
        locked.total_rows = total_rows
        locked.success_rows = len(normalized_rows)
        locked.error_rows = len(row_errors)
        locked.status = (
            ImportTaskStatus.PARTIAL_SUCCEEDED
            if row_errors
            else ImportTaskStatus.SUCCEEDED
        )
        locked.finished_at = timezone.now()
        locked.save(
            update_fields=[
                "total_rows",
                "success_rows",
                "error_rows",
                "status",
                "finished_at",
            ]
        )
        batch.published_at = locked.finished_at
        batch.save(update_fields=["published_at"])
        append_audit_log(
            request=SystemRequest(request_id=f"import-task-{locked.pk}"),
            tenant=upload.tenant,
            actor=locked.created_by,
            event="report.import_completed",
            object_type="ImportTask",
            object_id=locked.pk,
            task_id=str(locked.pk),
            after_data={
                "status": locked.status,
                "total_rows": total_rows,
                "success_rows": len(normalized_rows),
                "error_rows": len(row_errors),
                "batch_id": str(batch.pk),
                "report_type": upload.report_type,
                "published_metrics": len(published_metrics),
            },
        )
        return locked


@transaction.atomic
def reprocess_import(*, request, tenant_id, task_id) -> ImportTask:
    original = (
        ImportTask.objects.select_related("upload__profile")
        .filter(
            pk=task_id,
            upload__tenant_id=tenant_id,
        )
        .first()
    )
    if original is None:
        raise NotFound("Import task does not exist in the current tenant scope.")
    scope = require_profile_scope(
        user=request.user,
        tenant_id=tenant_id,
        profile_id=original.upload.profile_id,
        permission_code="reports.upload",
        minimum_level=ProfileAccessLevel.OPERATE,
    )
    celery_task_id = uuid.uuid4().hex
    task = ImportTask.objects.create(
        upload=original.upload,
        created_by=request.user,
        celery_task_id=celery_task_id,
        reprocessed_from=original,
    )
    append_audit_log(
        request=request,
        tenant=scope.membership.tenant,
        actor=request.user,
        event="report.reprocess_requested",
        object_type="ImportTask",
        object_id=task.pk,
        task_id=str(task.pk),
        after_data={"reprocessed_from": str(original.pk)},
    )
    from apps.reports.tasks import process_import_task

    transaction.on_commit(
        lambda: process_import_task.apply_async(
            args=[task.pk],
            task_id=celery_task_id,
        )
    )
    return task
