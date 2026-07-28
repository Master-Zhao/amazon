import hashlib
import json

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
def create_preview(*, request, tenant_id, profile_id, recommendation_ids):
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
    preview = ActionPreview.objects.create(
        tenant_id=tenant_id, profile=profile, created_by=request.user
    )
    items = _items(recommendations)
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
    if preview.created_by_id != request.user.pk or preview.status != PreviewStatus.DRAFT:
        raise ValidationError("当前状态不可提交")
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
        before={"status": PreviewStatus.DRAFT},
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
    *, request, item_id, result, actual_value, executed_at, note, idempotency_key
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
    record, created = ExecutionRecord.objects.get_or_create(
        item=item,
        idempotency_key=idempotency_key,
        defaults={
            "result": result,
            "actual_value": actual_value,
            "executed_at": executed_at,
            "note": note,
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
        append_audit(
            request=request,
            tenant=preview.tenant,
            event="EXECUTION_RECORDED",
            object_type="ExecutionItem",
            object_id=item.pk,
            after={"result": result},
        )
    return record


def evaluate_execution(execution_task):
    return EffectEvaluation.objects.create(
        execution_task=execution_task,
        status="BASELINE_READY",
        baseline={"versionId": execution_task.version_id},
        observed={},
    )

