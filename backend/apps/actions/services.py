import hashlib
import json
import uuid
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.actions.models import (
    ActionPreview,
    ActionPreviewVersion,
    ApprovalRecord,
    EffectEvaluation,
    ExecutionItem,
    ExecutionRecord,
    ExecutionTask,
    PreviewStatus,
)
from apps.audit.services import append_audit
from apps.permissions.models import ProfileAccessLevel
from apps.permissions.services import authorize
from apps.recommendations.models import Recommendation
from apps.tenants.models import MembershipRole, TenantType
from integrations.storage.local import LocalFileStorage


def _hash(items):
    return hashlib.sha256(
        json.dumps(items, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _items(recommendations):
    return [
        {
            "recommendationId": str(item.pk),
            "actionType": item.action_type,
            "objectType": item.object_type,
            "objectId": item.object_id,
            "beforeValue": item.before_value,
            "afterValue": item.after_value,
            "reason": item.reason,
            "evidence": item.evidence,
            "riskLevel": item.risk_level,
        }
        for item in recommendations
    ]


@transaction.atomic
def create_preview(
    *,
    request,
    tenant_id,
    profile_id,
    recommendation_ids,
    idempotency_key="",
):
    recommendations = list(
        Recommendation.objects.filter(
            id__in=recommendation_ids,
            tenant_id=tenant_id,
            profile_id=profile_id,
            status="OPEN",
        )
    )
    if not recommendations or len(recommendations) != len(set(recommendation_ids)):
        raise NotFound("建议不存在或越出当前范围")
    profile = recommendations[0].profile
    authorize(
        user=request.user,
        tenant_id=tenant_id,
        permission_code="actions.submit",
        profile=profile,
        minimum_profile_level=ProfileAccessLevel.OPERATE,
    )
    items = _items(recommendations)
    preview, created = ActionPreview.objects.get_or_create(
        tenant_id=tenant_id,
        idempotency_key=idempotency_key or uuid.uuid4().hex,
        defaults={"profile": profile, "created_by": request.user},
    )
    if not created:
        version = preview.versions.get(version=1)
        if preview.profile_id != profile.pk or version.items != items:
            raise ValidationError("幂等键已用于不同的 Action Preview 请求")
        return preview
    ActionPreviewVersion.objects.create(
        preview=preview, version=1, items=items, content_hash=_hash(items)
    )
    append_audit(
        request=request,
        tenant=preview.tenant,
        event="ACTION_PREVIEW_CREATED",
        object_type="ActionPreview",
        object_id=preview.pk,
        after={"status": preview.status, "version": 1},
    )
    return preview


def _locked_preview(preview_id):
    try:
        return ActionPreview.objects.select_for_update().select_related(
            "tenant", "profile", "created_by"
        ).get(pk=preview_id)
    except (ActionPreview.DoesNotExist, ValueError) as exc:
        raise NotFound("Action Preview 不存在") from exc


@transaction.atomic
def submit_preview(*, request, preview_id):
    preview = _locked_preview(preview_id)
    authorize(
        user=request.user,
        tenant_id=preview.tenant_id,
        permission_code="actions.submit",
        profile=preview.profile,
        minimum_profile_level=ProfileAccessLevel.OPERATE,
    )
    if preview.created_by_id != request.user.pk:
        raise ValidationError("当前状态不可提交")
    if preview.status == PreviewStatus.PENDING_APPROVAL:
        return preview
    if preview.status not in {PreviewStatus.DRAFT, PreviewStatus.RETURNED}:
        raise ValidationError("当前状态不可提交")
    before_status = preview.status
    version = preview.versions.get(version=preview.current_version)
    version.frozen_at = timezone.now()
    version.save(update_fields=["frozen_at"])
    preview.status = PreviewStatus.PENDING_APPROVAL
    preview.version_lock += 1
    preview.save(update_fields=["status", "version_lock"])
    append_audit(
        request=request,
        tenant=preview.tenant,
        event="ACTION_PREVIEW_SUBMITTED",
        object_type="ActionPreview",
        object_id=preview.pk,
        before={"status": before_status},
        after={"status": preview.status},
    )
    return preview


@transaction.atomic
def decide_preview(*, request, preview_id, decision, comment, idempotency_key):
    preview = _locked_preview(preview_id)
    authorize(
        user=request.user,
        tenant_id=preview.tenant_id,
        permission_code="actions.approve",
        profile=preview.profile,
        minimum_profile_level=ProfileAccessLevel.APPROVE,
    )
    existing_approval = ApprovalRecord.objects.filter(
        preview=preview, idempotency_key=idempotency_key
    ).first()
    if existing_approval is not None:
        if (
            existing_approval.actor_id != request.user.pk
            or existing_approval.decision != decision
            or existing_approval.comment != comment
        ):
            raise ValidationError("幂等键已用于不同的审批请求")
        return preview
    if preview.status != PreviewStatus.PENDING_APPROVAL:
        raise ValidationError("当前状态不可审批")
    if (
        preview.tenant.tenant_type in {TenantType.TEAM, TenantType.COMPANY}
        and preview.created_by_id == request.user.pk
    ):
        raise PermissionDenied("TEAM/COMPANY 提交人不能审批自己的方案")
    if decision not in {
        PreviewStatus.APPROVED,
        PreviewStatus.REJECTED,
        PreviewStatus.RETURNED,
    }:
        raise ValidationError("审批决定无效")
    version = preview.versions.get(version=preview.current_version)
    ApprovalRecord.objects.create(
        preview=preview,
        version=version,
        decision=decision,
        actor=request.user,
        comment=comment,
        idempotency_key=idempotency_key,
    )
    preview.status = decision
    if decision == PreviewStatus.RETURNED:
        preview.current_version += 1
        ActionPreviewVersion.objects.create(
            preview=preview,
            version=preview.current_version,
            items=version.items,
            content_hash=version.content_hash,
        )
    preview.version_lock += 1
    preview.save(update_fields=["status", "current_version", "version_lock"])
    if decision == PreviewStatus.APPROVED:
        execution = ExecutionTask.objects.create(preview=preview, version=version)
        ExecutionItem.objects.bulk_create(
            [
                ExecutionItem(task=execution, item_index=index, action=item)
                for index, item in enumerate(version.items)
            ]
        )
    append_audit(
        request=request,
        tenant=preview.tenant,
        event=f"ACTION_PREVIEW_{decision}",
        object_type="ActionPreview",
        object_id=preview.pk,
        after={"status": decision, "version": preview.current_version},
    )
    return preview


@transaction.atomic
def record_execution(
    *,
    request,
    item_id,
    result,
    actual_value,
    executed_at,
    note,
    idempotency_key,
    evidence_file=None,
):
    try:
        item = (
            ExecutionItem.objects.select_for_update()
            .select_related("task__preview__tenant", "task__preview__profile")
            .get(pk=item_id)
        )
    except (ExecutionItem.DoesNotExist, ValueError) as exc:
        raise NotFound("执行项不存在") from exc
    preview = item.task.preview
    authorize(
        user=request.user,
        tenant_id=preview.tenant_id,
        permission_code="actions.execute",
        profile=preview.profile,
        minimum_profile_level=ProfileAccessLevel.EXECUTE,
    )
    if result not in {"SUCCEEDED", "FAILED", "SKIPPED"}:
        raise ValidationError("执行结果无效")
    existing_record = ExecutionRecord.objects.filter(item=item).first()
    if existing_record is not None:
        if existing_record.idempotency_key == idempotency_key:
            return existing_record
        raise ValidationError("执行项已有回填记录")
    evidence_path = ""
    if evidence_file is not None:
        if evidence_file.size > settings.ACTION_EVIDENCE_MAX_BYTES:
            raise ValidationError({"evidence": "执行证据文件超过大小限制"})
        if Path(evidence_file.name).suffix.lower() not in {
            ".jpg",
            ".jpeg",
            ".png",
            ".pdf",
            ".txt",
        }:
            raise ValidationError({"evidence": "仅支持 JPG、PNG、PDF 或 TXT"})
        evidence_path = LocalFileStorage().save_stream(
            namespace=f"execution-evidence/{preview.tenant_id}",
            filename=evidence_file.name,
            chunks=evidence_file.chunks(),
        ).path
    record, created = ExecutionRecord.objects.get_or_create(
        item=item,
        idempotency_key=idempotency_key,
        defaults={
            "result": result,
            "actual_value": actual_value,
            "executed_at": executed_at,
            "note": note,
            "evidence_path": evidence_path,
            "actor": request.user,
        },
    )
    if created:
        item.status = result
        item.save(update_fields=["status"])
        statuses = list(item.task.items.values_list("status", flat=True))
        item.task.status = (
            "COMPLETED" if all(value != "PENDING" for value in statuses) else "PARTIAL"
        )
        item.task.save(update_fields=["status"])
        if item.task.status == "COMPLETED":
            from apps.actions.tasks import evaluate_effects

            execution_task_id = str(item.task_id)
            transaction.on_commit(
                lambda: evaluate_effects.delay(execution_task_id)
            )
        append_audit(
            request=request,
            tenant=preview.tenant,
            event="EXECUTION_RECORDED",
            object_type="ExecutionItem",
            object_id=item.pk,
            after={"result": result},
        )
    return record


@transaction.atomic
def evaluate_execution(execution_task_id):
    try:
        execution_task = (
            ExecutionTask.objects.select_for_update()
            .select_related("version")
            .get(pk=execution_task_id)
        )
    except (ExecutionTask.DoesNotExist, ValueError) as exc:
        raise NotFound("执行任务不存在") from exc
    if execution_task.status != "COMPLETED":
        raise ValidationError("执行任务尚未完成")
    evaluation, _ = EffectEvaluation.objects.get_or_create(
        execution_task=execution_task,
        defaults={
            "status": "BASELINE_READY",
            "baseline": {
                "versionId": execution_task.version_id,
                "completedItemCount": execution_task.items.count(),
            },
            "observed": {},
        },
    )
    return evaluation
