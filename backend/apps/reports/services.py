import gzip
import json
import uuid
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.advertising.models import (
    AdGroup,
    Campaign,
    EntityState,
    Keyword,
    MatchType,
    ProductTarget,
    SearchTerm,
)
from apps.permissions.models import ProfileAccessLevel
from apps.permissions.services import authorize
from apps.reports.models import (
    ImportBatch,
    ImportRowError,
    ImportStatus,
    ImportTask,
    ReportType,
    ReportUpload,
)
from apps.reports.parsers import ReportFileError, iter_rows
from apps.stores.models import AdvertisingProfile
from integrations.storage.local import LocalFileStorage

REQUIRED_FIELDS = {
    ReportType.CAMPAIGN: {"campaign_id", "campaign_name", "state", "currency"},
    ReportType.TARGETING: {
        "campaign_id",
        "campaign_name",
        "ad_group_id",
        "ad_group_name",
        "targeting_type",
        "targeting_id",
        "targeting_text",
        "state",
        "currency",
    },
    ReportType.SEARCH_TERM: {
        "campaign_id",
        "campaign_name",
        "search_term",
        "targeting_text",
        "currency",
    },
}


def _decimal(value, field, *, nullable=True):
    if value in {None, ""} and nullable:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field}:INVALID_DECIMAL") from exc
    if parsed < 0:
        raise ValueError(f"{field}:NEGATIVE")
    return parsed


def _campaign(profile, row, batch):
    state = str(row["state"]).upper()
    if state not in EntityState.values:
        raise ValueError("state:INVALID_STATE")
    campaign, _ = Campaign.objects.update_or_create(
        profile=profile,
        external_campaign_id=str(row["campaign_id"]),
        defaults={
            "name": str(row["campaign_name"]),
            "state": state,
            "daily_budget": _decimal(row.get("budget"), "budget"),
            "currency": str(row["currency"]).upper(),
            "source_batch_id": batch.pk,
        },
    )
    return campaign


def _normalize_row(profile, report_type, row, batch):
    if row.get("profile_id") and str(row["profile_id"]) != profile.external_profile_id:
        raise ValueError("profile_id:PROFILE_MISMATCH")
    missing = [field for field in REQUIRED_FIELDS[report_type] if not row.get(field)]
    if missing:
        raise ValueError(f"{missing[0]}:REQUIRED")
    if str(row["currency"]).upper() != profile.currency:
        raise ValueError("currency:PROFILE_MISMATCH")
    campaign = _campaign(
        profile,
        {
            **row,
            "state": row.get("campaign_state") or row.get("state") or "ENABLED",
        },
        batch,
    )
    if report_type == ReportType.CAMPAIGN:
        return {"campaignId": str(campaign.pk)}
    if report_type == ReportType.TARGETING:
        ad_group, _ = AdGroup.objects.update_or_create(
            campaign=campaign,
            external_ad_group_id=str(row["ad_group_id"]),
            defaults={
                "name": str(row["ad_group_name"]),
                "state": str(row.get("ad_group_state") or "ENABLED").upper(),
            },
        )
        target_type = str(row["targeting_type"]).upper()
        if target_type == "KEYWORD":
            match_type = str(row.get("match_type") or "EXACT").upper()
            if match_type not in MatchType.values:
                raise ValueError("match_type:INVALID")
            target, _ = Keyword.objects.update_or_create(
                ad_group=ad_group,
                external_keyword_id=str(row["targeting_id"]),
                defaults={
                    "text": str(row["targeting_text"]),
                    "match_type": match_type,
                    "state": str(row["state"]).upper(),
                    "bid": _decimal(row.get("bid"), "bid"),
                },
            )
        elif target_type == "PRODUCT":
            target, _ = ProductTarget.objects.update_or_create(
                ad_group=ad_group,
                external_target_id=str(row["targeting_id"]),
                defaults={
                    "expression": str(row["targeting_text"]),
                    "state": str(row["state"]).upper(),
                    "bid": _decimal(row.get("bid"), "bid"),
                },
            )
        else:
            raise ValueError("targeting_type:INVALID")
        return {"targetId": str(target.pk), "targetingType": target_type}
    term, _ = SearchTerm.objects.update_or_create(
        profile=profile,
        query_text=str(row["search_term"]),
        targeting_text=str(row["targeting_text"]),
        defaults={
            "campaign": campaign,
            "source_batch_id": batch.pk,
        },
    )
    return {"searchTermId": str(term.pk)}


@transaction.atomic
def create_upload_task(*, user, tenant_id, profile_id, report_type, uploaded_file, idempotency_key):
    try:
        profile = AdvertisingProfile.objects.select_related(
            "store_marketplace__store__tenant"
        ).get(pk=profile_id)
    except (AdvertisingProfile.DoesNotExist, ValueError) as exc:
        from rest_framework.exceptions import NotFound

        raise NotFound("广告 Profile 不存在") from exc
    authorize(
        user=user,
        tenant_id=tenant_id,
        permission_code="reports.import",
        profile=profile,
        minimum_profile_level=ProfileAccessLevel.OPERATE,
    )
    if report_type not in ReportType.values:
        raise ValidationError({"reportType": "不支持的报表类型"})
    if uploaded_file.size > 25 * 1024 * 1024:
        raise ValidationError({"file": "文件超过 25 MiB 保守限制"})
    suffix = str(uploaded_file.name).lower()
    if not suffix.endswith((".csv", ".xlsx")):
        raise ValidationError({"file": "仅支持 CSV 或 XLSX"})
    stored = LocalFileStorage().save_stream(
        namespace="reports", filename=uploaded_file.name, chunks=uploaded_file.chunks()
    )
    duplicate = ReportUpload.objects.filter(
        profile=profile, report_type=report_type, sha256=stored.sha256
    ).exists()
    upload = ReportUpload.objects.create(
        tenant_id=tenant_id,
        profile=profile,
        report_type=report_type,
        original_name=uploaded_file.name,
        content_type=uploaded_file.content_type or "application/octet-stream",
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        storage_path=stored.path,
        uploaded_by=user,
        is_duplicate=duplicate,
    )
    task = ImportTask.objects.create(
        upload=upload,
        status=ImportStatus.QUEUED,
        requested_by=user,
        idempotency_key=idempotency_key or uuid.uuid4().hex,
    )
    from apps.reports.tasks import process_import_task

    transaction.on_commit(lambda: process_import_task.delay(str(task.pk)))
    return task


def process_task(task_id):
    with transaction.atomic():
        task = ImportTask.objects.select_for_update().select_related("upload__profile").get(
            pk=task_id
        )
        if task.status != ImportStatus.QUEUED:
            return task
        task.status = ImportStatus.RUNNING
        task.started_at = timezone.now()
        task.save(update_fields=["status", "started_at"])
        batch = ImportBatch.objects.create(task=task, status=ImportStatus.RUNNING)
    normalized = []
    total = succeeded = failed = 0
    try:
        for row_number, row in iter_rows(task.upload.storage_path):
            total += 1
            try:
                with transaction.atomic():
                    normalized.append(
                        _normalize_row(task.upload.profile, task.upload.report_type, row, batch)
                    )
                succeeded += 1
            except (ValueError, IntegrityError) as exc:
                failed += 1
                detail = str(exc).split(":", 1)
                ImportRowError.objects.create(
                    batch=batch,
                    row_number=row_number,
                    code=detail[-1] if len(detail) > 1 else "INVALID_ROW",
                    field=detail[0] if len(detail) > 1 else "",
                    message=str(exc)[:500],
                    raw_excerpt={key: str(value)[:100] for key, value in row.items()},
                )
    except ReportFileError as exc:
        task.status = ImportStatus.FAILED
        task.error_code = str(exc)
        task.error_message = "文件级校验失败"
    else:
        if total == 0 or succeeded == 0:
            task.status = ImportStatus.FAILED
        elif failed:
            task.status = ImportStatus.PARTIAL_SUCCEEDED
        else:
            task.status = ImportStatus.SUCCEEDED
    payload = gzip.compress(
        b"\n".join(json.dumps(item).encode("utf-8") for item in normalized)
    )
    normalized_path = LocalFileStorage().write_bytes(
        namespace="normalized",
        filename=f"{batch.pk}.jsonl.gz",
        content=payload,
    )
    now = timezone.now()
    with transaction.atomic():
        batch = ImportBatch.objects.select_for_update().get(pk=batch.pk)
        batch.status = task.status
        batch.total_rows = total
        batch.succeeded_rows = succeeded
        batch.failed_rows = failed
        batch.normalized_rows_path = normalized_path
        batch.completed_at = now
        batch.save()
        task.completed_at = now
        task.save(
            update_fields=["status", "completed_at", "error_code", "error_message"]
        )
    return task


@transaction.atomic
def reprocess(*, user, tenant_id, task):
    authorize(
        user=user,
        tenant_id=tenant_id,
        permission_code="reports.import",
        profile=task.upload.profile,
        minimum_profile_level=ProfileAccessLevel.OPERATE,
    )
    new_task = ImportTask.objects.create(
        upload=task.upload,
        status=ImportStatus.QUEUED,
        requested_by=user,
        idempotency_key=uuid.uuid4().hex,
    )
    from apps.reports.tasks import process_import_task

    transaction.on_commit(lambda: process_import_task.delay(str(new_task.pk)))
    return new_task
