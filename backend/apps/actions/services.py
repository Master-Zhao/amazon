import hashlib
import json
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.serializers import ValidationError

from apps.actions.models import (
    ActionPreview,
    ActionPreviewStatus,
    ActionPreviewVersion,
    ApprovalDecision,
    ApprovalRecord,
    EffectEvaluation,
    ExecutionOutcome,
    ExecutionRecord,
)
from apps.advertising.models import (
    AdGroup,
    Campaign,
    EntityState,
    Keyword,
    MatchType,
    ProductTarget,
)
from apps.audit.services import append_audit_log
from apps.permissions.models import ProfileAccessLevel
from apps.permissions.services import require_profile_scope
from apps.recommendations.models import (
    ActionType,
    Recommendation,
    RecommendationRevision,
)
from apps.tenants.models import MembershipRole, TenantType
from integrations.storage.local import LocalFileStorage


def _revision_payload(revision: RecommendationRevision) -> dict[str, object]:
    return {
        "schemaVersion": revision.schema_version,
        "actionType": revision.action_type,
        "objectType": revision.object_type,
        "objectId": revision.object_id,
        "beforeValue": revision.before_value,
        "afterValue": revision.after_value,
        "reason": revision.reason,
        "evidence": revision.evidence,
        "riskLevel": revision.risk_level,
    }


def _decimal_value(
    payload: dict,
    field: str,
    *,
    minimum: Decimal,
    maximum: Decimal,
) -> Decimal:
    try:
        value = Decimal(str(payload[field]))
    except (KeyError, InvalidOperation) as exc:
        raise ValidationError({field: ["A valid decimal value is required."]}) from exc
    if not minimum <= value <= maximum:
        raise ValidationError(
            {field: [f"Value must be between {minimum} and {maximum}."]}
        )
    return value


def _state_value(payload: dict, field: str = "state") -> str:
    value = str(payload.get(field, ""))
    if value not in {EntityState.ENABLED, EntityState.PAUSED}:
        raise ValidationError(
            {field: ["Only ENABLED and PAUSED are supported; deletion is forbidden."]}
        )
    return value


def _validate_named_state_action(*, action_type: str, proposed_state: str) -> None:
    required_state = {
        ActionType.ENABLE_CAMPAIGN: EntityState.ENABLED,
        ActionType.PAUSE_CAMPAIGN: EntityState.PAUSED,
        ActionType.ENABLE_KEYWORD: EntityState.ENABLED,
        ActionType.PAUSE_KEYWORD: EntityState.PAUSED,
        ActionType.ENABLE_TARGET: EntityState.ENABLED,
        ActionType.PAUSE_TARGET: EntityState.PAUSED,
    }.get(action_type)
    if required_state is not None and proposed_state != required_state:
        raise ValidationError(
            {"after_value": [f"{action_type} requires state {required_state}."]}
        )


def _validate_action_payload(*, payload: dict, profile_id: int):
    action_type = payload.get("actionType")
    object_type = payload.get("objectType")
    object_id = payload.get("objectId")
    before = payload.get("beforeValue")
    after = payload.get("afterValue")
    if action_type not in ActionType.values:
        raise ValidationError({"action_type": ["Unsupported action type."]})
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ValidationError("beforeValue and afterValue must be objects.")

    if action_type in {
        ActionType.UPDATE_CAMPAIGN_BUDGET,
        ActionType.ENABLE_CAMPAIGN,
        ActionType.PAUSE_CAMPAIGN,
        ActionType.SET_CAMPAIGN_STATE,
    }:
        if object_type != "Campaign":
            raise ValidationError("Campaign actions require objectType Campaign.")
        target = Campaign.objects.filter(
            pk=object_id,
            profile_id=profile_id,
        ).first()
        if target is None:
            raise NotFound("Campaign does not exist in the current Profile scope.")
        if action_type == ActionType.UPDATE_CAMPAIGN_BUDGET:
            expected = _decimal_value(
                before,
                "dailyBudget",
                minimum=settings.ACTION_MIN_DAILY_BUDGET,
                maximum=settings.ACTION_MAX_DAILY_BUDGET,
            )
            proposed = _decimal_value(
                after,
                "dailyBudget",
                minimum=settings.ACTION_MIN_DAILY_BUDGET,
                maximum=settings.ACTION_MAX_DAILY_BUDGET,
            )
            if (
                target.daily_budget is None
                or expected != target.daily_budget
                or before.get("currency") != target.currency_code
                or after.get("currency") != target.currency_code
            ):
                raise ValidationError(
                    {"before_value": ["Campaign budget or currency drift detected."]}
                )
            if proposed == expected:
                raise ValidationError({"after_value": ["Budget must change."]})
        else:
            expected_state = _state_value(before)
            proposed_state = _state_value(after)
            _validate_named_state_action(
                action_type=action_type,
                proposed_state=proposed_state,
            )
            if target.state != expected_state:
                raise ValidationError(
                    {"before_value": ["Campaign state drift detected."]}
                )
            if proposed_state == expected_state:
                raise ValidationError({"after_value": ["State must change."]})
        return target

    if action_type in {
        ActionType.UPDATE_KEYWORD_BID,
        ActionType.ENABLE_KEYWORD,
        ActionType.PAUSE_KEYWORD,
        ActionType.SET_KEYWORD_STATE,
    }:
        if object_type != "Keyword":
            raise ValidationError("Keyword actions require objectType Keyword.")
        target = Keyword.objects.select_related(
            "ad_group__campaign"
        ).filter(
            pk=object_id,
            ad_group__campaign__profile_id=profile_id,
        ).first()
        if target is None:
            raise NotFound("Keyword does not exist in the current Profile scope.")
        campaign = target.ad_group.campaign
        if action_type == ActionType.UPDATE_KEYWORD_BID:
            expected = _decimal_value(
                before,
                "bid",
                minimum=settings.ACTION_MIN_BID,
                maximum=settings.ACTION_MAX_BID,
            )
            proposed = _decimal_value(
                after,
                "bid",
                minimum=settings.ACTION_MIN_BID,
                maximum=settings.ACTION_MAX_BID,
            )
            if (
                target.bid is None
                or target.bid != expected
                or before.get("currency") != campaign.currency_code
                or after.get("currency") != campaign.currency_code
            ):
                raise ValidationError(
                    {"before_value": ["Keyword bid or currency drift detected."]}
                )
            if proposed == expected:
                raise ValidationError({"after_value": ["Bid must change."]})
        else:
            expected_state = _state_value(before)
            proposed_state = _state_value(after)
            _validate_named_state_action(
                action_type=action_type,
                proposed_state=proposed_state,
            )
            if target.state != expected_state:
                raise ValidationError(
                    {"before_value": ["Keyword state drift detected."]}
                )
            if proposed_state == expected_state:
                raise ValidationError({"after_value": ["State must change."]})
        return target

    if action_type in {
        ActionType.UPDATE_TARGET_BID,
        ActionType.UPDATE_PRODUCT_TARGET_BID,
        ActionType.ENABLE_TARGET,
        ActionType.PAUSE_TARGET,
        ActionType.SET_PRODUCT_TARGET_STATE,
    }:
        if object_type != "ProductTarget":
            raise ValidationError(
                "Product Target actions require objectType ProductTarget."
            )
        target = ProductTarget.objects.select_related(
            "ad_group__campaign"
        ).filter(
            pk=object_id,
            ad_group__campaign__profile_id=profile_id,
        ).first()
        if target is None:
            raise NotFound(
                "Product Target does not exist in the current Profile scope."
            )
        campaign = target.ad_group.campaign
        if action_type in {
            ActionType.UPDATE_TARGET_BID,
            ActionType.UPDATE_PRODUCT_TARGET_BID,
        }:
            expected = _decimal_value(
                before,
                "bid",
                minimum=settings.ACTION_MIN_BID,
                maximum=settings.ACTION_MAX_BID,
            )
            proposed = _decimal_value(
                after,
                "bid",
                minimum=settings.ACTION_MIN_BID,
                maximum=settings.ACTION_MAX_BID,
            )
            if (
                target.bid is None
                or target.bid != expected
                or before.get("currency") != campaign.currency_code
                or after.get("currency") != campaign.currency_code
            ):
                raise ValidationError(
                    {"before_value": ["Product Target bid or currency drift detected."]}
                )
            if proposed == expected:
                raise ValidationError({"after_value": ["Bid must change."]})
        else:
            expected_state = _state_value(before)
            proposed_state = _state_value(after)
            _validate_named_state_action(
                action_type=action_type,
                proposed_state=proposed_state,
            )
            if target.state != expected_state:
                raise ValidationError(
                    {"before_value": ["Product Target state drift detected."]}
                )
            if proposed_state == expected_state:
                raise ValidationError({"after_value": ["State must change."]})
        return target

    if action_type in {ActionType.ADD_KEYWORD, ActionType.CREATE_KEYWORD}:
        if object_type != "AdGroup":
            raise ValidationError("CREATE_KEYWORD requires objectType AdGroup.")
        target = AdGroup.objects.select_related("campaign").filter(
            pk=object_id,
            campaign__profile_id=profile_id,
        ).first()
        if target is None:
            raise NotFound("AdGroup does not exist in the current Profile scope.")
        text = str(after.get("keywordText", "")).strip()
        if not text or len(text) > 500:
            raise ValidationError({"keyword_text": ["Use 1 to 500 characters."]})
        if after.get("matchType") not in MatchType.values:
            raise ValidationError({"match_type": ["Use BROAD, PHRASE or EXACT."]})
        _decimal_value(
            after,
            "bid",
            minimum=settings.ACTION_MIN_BID,
            maximum=settings.ACTION_MAX_BID,
        )
        if after.get("currency") != target.campaign.currency_code:
            raise ValidationError({"currency": ["Currency does not match Campaign."]})
        return target

    if action_type in {
        ActionType.ADD_NEGATIVE_KEYWORD,
        ActionType.CREATE_NEGATIVE_KEYWORD,
    }:
        negative_scope = str(after.get("negativeScope", ""))
        if negative_scope == "CAMPAIGN" and object_type == "Campaign":
            target = Campaign.objects.filter(
                pk=object_id,
                profile_id=profile_id,
            ).first()
        elif negative_scope == "AD_GROUP" and object_type == "AdGroup":
            target = AdGroup.objects.filter(
                pk=object_id,
                campaign__profile_id=profile_id,
            ).first()
        else:
            raise ValidationError(
                {
                    "negative_scope": [
                        "Use CAMPAIGN with Campaign or AD_GROUP with AdGroup."
                    ]
                }
            )
        if target is None:
            raise NotFound(
                "Negative Keyword parent does not exist in the current Profile scope."
            )
        text = str(after.get("keywordText", "")).strip()
        if not text or len(text) > 500:
            raise ValidationError({"keyword_text": ["Use 1 to 500 characters."]})
        if after.get("matchType") not in MatchType.values:
            raise ValidationError({"match_type": ["Use BROAD, PHRASE or EXACT."]})
        return target

    raise ValidationError("Unsupported Action Preview type.")


def validate_action_payload(*, payload: dict, profile_id: int):
    """Validate one of the supported V1 actions against the current Profile state."""
    return _validate_action_payload(payload=payload, profile_id=profile_id)


def _state_version(target) -> str:
    payload = json.dumps(
        {
            "object_type": target.__class__.__name__,
            "object_id": target.pk,
            "daily_budget": str(getattr(target, "daily_budget", None)),
            "bid": str(getattr(target, "bid", None)),
            "currency": getattr(target, "currency_code", None),
            "state": getattr(target, "state", None),
            "updated_at": (
                target.updated_at.isoformat()
                if getattr(target, "updated_at", None)
                else None
            ),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _current_version(preview: ActionPreview) -> ActionPreviewVersion:
    version = preview.versions.filter(
        version_number=preview.current_version_number
    ).first()
    if version is None:
        raise ValidationError("Action Preview version is missing.")
    return version


@transaction.atomic
def create_action_preview(*, request, tenant_id, recommendation_id) -> ActionPreview:
    recommendation = (
        Recommendation.objects.select_related(
            "tenant",
            "profile",
            "campaign",
        )
        .prefetch_related("revisions")
        .filter(pk=recommendation_id, tenant_id=tenant_id)
        .first()
    )
    if recommendation is None:
        raise NotFound("Recommendation does not exist in the current tenant scope.")
    scope = require_profile_scope(
        user=request.user,
        tenant_id=tenant_id,
        profile_id=recommendation.profile_id,
        permission_code="actions.operate",
        minimum_level=ProfileAccessLevel.OPERATE,
    )
    revision = recommendation.revisions.filter(
        revision_number=recommendation.current_revision_number
    ).first()
    if revision is None:
        raise ValidationError("Recommendation revision is missing.")
    existing = ActionPreview.objects.filter(
        recommendation_revision=revision,
        created_by=request.user,
    ).first()
    if existing is not None:
        return existing
    action_payload = _revision_payload(revision)
    target = _validate_action_payload(
        payload=action_payload,
        profile_id=scope.profile.pk,
    )
    preview = ActionPreview.objects.create(
        tenant=scope.membership.tenant,
        profile=scope.profile,
        recommendation_revision=revision,
        created_by=request.user,
    )
    ActionPreviewVersion.objects.create(
        preview=preview,
        version_number=1,
        action_payload=action_payload,
        object_state_version=_state_version(target),
        created_by=request.user,
    )
    append_audit_log(
        request=request,
        tenant=scope.membership.tenant,
        actor=request.user,
        event="action_preview.created",
        object_type="ActionPreview",
        object_id=preview.pk,
        after_data={
            "recommendation_id": str(recommendation.pk),
            "version": 1,
            "action_type": revision.action_type,
        },
    )
    return preview


@transaction.atomic
def submit_action_preview(*, request, tenant_id, preview_id) -> ActionPreview:
    preview = (
        ActionPreview.objects.select_for_update()
        .select_related("recommendation_revision", "tenant", "profile")
        .filter(pk=preview_id, tenant_id=tenant_id)
        .first()
    )
    if preview is None:
        raise NotFound("Action Preview does not exist in the current tenant scope.")
    scope = require_profile_scope(
        user=request.user,
        tenant_id=tenant_id,
        profile_id=preview.profile_id,
        permission_code="actions.operate",
        minimum_level=ProfileAccessLevel.OPERATE,
    )
    if preview.created_by_id != request.user.pk:
        raise PermissionDenied("Only the creator can submit this Action Preview.")
    if preview.status == ActionPreviewStatus.PENDING_APPROVAL:
        return preview
    if preview.status not in {
        ActionPreviewStatus.DRAFT,
        ActionPreviewStatus.RETURNED,
    }:
        raise ValidationError(
            {
                "status": [
                    "Only a DRAFT or newly versioned RETURNED Action Preview "
                    "can be submitted."
                ]
            }
        )
    version = _current_version(preview)
    if preview.status == ActionPreviewStatus.RETURNED:
        returned_version = (
            preview.approval_records.filter(
                decision=ApprovalDecision.RETURNED,
            )
            .order_by("-created_at")
            .values_list("preview_version__version_number", flat=True)
            .first()
        )
        if returned_version is None or version.version_number <= returned_version:
            raise ValidationError(
                {
                    "version": [
                        "Create a new immutable version before resubmitting "
                        "a returned Action Preview."
                    ]
                }
            )
    target = _validate_action_payload(
        payload=version.action_payload,
        profile_id=scope.profile.pk,
    )
    if _state_version(target) != version.object_state_version:
        raise ValidationError(
            {"before_value": ["Object state drift detected since preview creation."]}
        )
    before_status = preview.status
    preview.status = ActionPreviewStatus.PENDING_APPROVAL
    preview.submitted_by = request.user
    preview.save(update_fields=["status", "submitted_by", "updated_at"])
    append_audit_log(
        request=request,
        tenant=scope.membership.tenant,
        actor=request.user,
        event="action_preview.submitted",
        object_type="ActionPreview",
        object_id=preview.pk,
        before_data={"status": before_status},
        after_data={
            "status": ActionPreviewStatus.PENDING_APPROVAL,
            "version": preview.current_version_number,
        },
    )
    return preview


@transaction.atomic
def create_returned_preview_version(
    *,
    request,
    tenant_id,
    preview_id,
    action_payload: dict,
) -> ActionPreview:
    preview = (
        ActionPreview.objects.select_for_update()
        .select_related("tenant", "profile")
        .filter(pk=preview_id, tenant_id=tenant_id)
        .first()
    )
    if preview is None:
        raise NotFound("Action Preview does not exist in the current tenant scope.")
    scope = require_profile_scope(
        user=request.user,
        tenant_id=tenant_id,
        profile_id=preview.profile_id,
        permission_code="actions.operate",
        minimum_level=ProfileAccessLevel.OPERATE,
    )
    if preview.created_by_id != request.user.pk:
        raise PermissionDenied("Only the creator can revise this Action Preview.")
    if preview.status != ActionPreviewStatus.RETURNED:
        raise ValidationError(
            {"status": ["Only a RETURNED Action Preview can create a new version."]}
        )
    previous = _current_version(preview)
    for immutable_key in ("actionType", "objectType", "objectId"):
        if action_payload.get(immutable_key) != previous.action_payload.get(
            immutable_key
        ):
            raise ValidationError(
                {
                    immutable_key: [
                        "Returned versions cannot change the action target or type."
                    ]
                }
            )
    target = _validate_action_payload(
        payload=action_payload,
        profile_id=scope.profile.pk,
    )
    next_number = preview.current_version_number + 1
    ActionPreviewVersion.objects.create(
        preview=preview,
        version_number=next_number,
        action_payload=action_payload,
        object_state_version=_state_version(target),
        created_by=request.user,
    )
    preview.current_version_number = next_number
    preview.save(update_fields=["current_version_number", "updated_at"])
    append_audit_log(
        request=request,
        tenant=scope.membership.tenant,
        actor=request.user,
        event="action_preview.version_created",
        object_type="ActionPreview",
        object_id=preview.pk,
        before_data={"version": previous.version_number},
        after_data={"version": next_number},
    )
    return preview


@transaction.atomic
def withdraw_action_preview(*, request, tenant_id, preview_id) -> ActionPreview:
    preview = (
        ActionPreview.objects.select_for_update()
        .select_related("tenant", "profile")
        .filter(pk=preview_id, tenant_id=tenant_id)
        .first()
    )
    if preview is None:
        raise NotFound("Action Preview does not exist in the current tenant scope.")
    scope = require_profile_scope(
        user=request.user,
        tenant_id=tenant_id,
        profile_id=preview.profile_id,
        permission_code="actions.operate",
        minimum_level=ProfileAccessLevel.OPERATE,
    )
    if preview.created_by_id != request.user.pk:
        raise PermissionDenied("Only the creator can withdraw this Action Preview.")
    if preview.status == ActionPreviewStatus.WITHDRAWN:
        return preview
    if preview.status not in {
        ActionPreviewStatus.DRAFT,
        ActionPreviewStatus.PENDING_APPROVAL,
        ActionPreviewStatus.RETURNED,
    }:
        raise ValidationError(
            {"status": ["This Action Preview can no longer be withdrawn."]}
        )
    before_status = preview.status
    preview.status = ActionPreviewStatus.WITHDRAWN
    preview.save(update_fields=["status", "updated_at"])
    append_audit_log(
        request=request,
        tenant=scope.membership.tenant,
        actor=request.user,
        event="action_preview.withdrawn",
        object_type="ActionPreview",
        object_id=preview.pk,
        before_data={"status": before_status},
        after_data={"status": ActionPreviewStatus.WITHDRAWN},
    )
    return preview


@transaction.atomic
def decide_action_preview(
    *,
    request,
    tenant_id,
    preview_id,
    decision: str,
    comment: str,
    idempotency_key: str,
) -> tuple[ActionPreview, ApprovalRecord]:
    if decision not in ApprovalDecision.values:
        raise ValidationError({"decision": ["Invalid approval decision."]})
    previous = ApprovalRecord.objects.filter(
        idempotency_key=idempotency_key
    ).select_related("preview").first()
    if previous is not None:
        if previous.preview_id != int(preview_id) or previous.decision != decision:
            raise ValidationError(
                {"idempotency_key": ["Key was already used for another decision."]}
            )
        return previous.preview, previous
    preview = (
        ActionPreview.objects.select_for_update()
        .select_related(
            "tenant",
            "profile",
            "submitted_by",
            "recommendation_revision",
        )
        .filter(pk=preview_id, tenant_id=tenant_id)
        .first()
    )
    if preview is None:
        raise NotFound("Action Preview does not exist in the current tenant scope.")
    scope = require_profile_scope(
        user=request.user,
        tenant_id=tenant_id,
        profile_id=preview.profile_id,
        permission_code="approvals.approve",
        minimum_level=ProfileAccessLevel.APPROVE,
    )
    if preview.status != ActionPreviewStatus.PENDING_APPROVAL:
        raise ValidationError(
            {"status": ["Only PENDING_APPROVAL can be decided."]}
        )
    is_personal_owner = (
        scope.membership.tenant.tenant_type == TenantType.PERSONAL
        and scope.membership.membership_role == MembershipRole.OWNER
    )
    if preview.submitted_by_id == request.user.pk and not is_personal_owner:
        raise PermissionDenied(
            "TEAM/COMPANY submitters cannot approve their own Action Preview."
        )
    version = _current_version(preview)
    if decision == ApprovalDecision.APPROVED:
        target = _validate_action_payload(
            payload=version.action_payload,
            profile_id=scope.profile.pk,
        )
        if _state_version(target) != version.object_state_version:
            raise ValidationError(
                {
                    "before_value": [
                        "Object state drift detected since preview creation."
                    ]
                }
            )
    try:
        record = ApprovalRecord.objects.create(
            preview=preview,
            preview_version=version,
            decision=decision,
            comment=comment,
            decided_by=request.user,
            idempotency_key=idempotency_key,
        )
    except IntegrityError as exc:
        raise ValidationError(
            {"idempotency_key": ["Concurrent duplicate approval detected."]}
        ) from exc
    preview.status = decision
    preview.save(update_fields=["status", "updated_at"])
    append_audit_log(
        request=request,
        tenant=scope.membership.tenant,
        actor=request.user,
        event="action_preview.decided",
        object_type="ActionPreview",
        object_id=preview.pk,
        before_data={"status": ActionPreviewStatus.PENDING_APPROVAL},
        after_data={
            "status": decision,
            "version": version.version_number,
            "comment": comment,
        },
    )
    return preview, record


def _store_execution_evidence(
    *,
    tenant_id: int,
    evidence_file,
) -> dict[str, object]:
    if evidence_file is None:
        return {}
    suffix = Path(evidence_file.name).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".pdf", ".txt"}:
        raise ValidationError(
            {"evidence_file": ["Only JPG, PNG, PDF or TXT evidence is accepted."]}
        )
    declared_size = int(evidence_file.size or 0)
    if declared_size <= 0:
        raise ValidationError({"evidence_file": ["Evidence file is empty."]})
    if declared_size > settings.ACTION_EVIDENCE_MAX_BYTES:
        raise ValidationError(
            {"evidence_file": ["Evidence file exceeds the configured size limit."]}
        )
    storage = LocalFileStorage()
    key = f"{tenant_id}/execution-evidence/{uuid.uuid4().hex}{suffix}"
    digest = hashlib.sha256()
    observed_size = 0

    def checked_chunks():
        nonlocal observed_size
        for chunk in evidence_file.chunks():
            observed_size += len(chunk)
            if observed_size > settings.ACTION_EVIDENCE_MAX_BYTES:
                raise ValidationError(
                    {
                        "evidence_file": [
                            "Evidence file exceeds the configured size limit."
                        ]
                    }
                )
            digest.update(chunk)
            yield chunk

    try:
        storage.save(key=key, chunks=checked_chunks())
    except Exception:
        storage.delete(key=key)
        raise
    return {
        "storageKey": key,
        "originalFilename": Path(evidence_file.name).name,
        "contentType": evidence_file.content_type or "application/octet-stream",
        "sizeBytes": observed_size,
        "sha256": digest.hexdigest(),
    }


@transaction.atomic
def record_manual_execution(
    *,
    request,
    tenant_id,
    preview_id,
    outcome: str,
    actual_value: dict,
    executed_at,
    note: str,
    evidence_metadata: dict,
    idempotency_key: str,
    evidence_file=None,
) -> tuple[ActionPreview, ExecutionRecord]:
    if outcome not in ExecutionOutcome.values:
        raise ValidationError({"outcome": ["Invalid execution outcome."]})
    previous = ExecutionRecord.objects.filter(
        idempotency_key=idempotency_key
    ).select_related("preview").first()
    if previous is not None:
        if previous.preview_id != int(preview_id) or previous.outcome != outcome:
            raise ValidationError(
                {"idempotency_key": ["Key was already used for another execution."]}
            )
        return previous.preview, previous
    preview = (
        ActionPreview.objects.select_for_update()
        .select_related("tenant", "profile")
        .filter(pk=preview_id, tenant_id=tenant_id)
        .first()
    )
    if preview is None:
        raise NotFound("Action Preview does not exist in the current tenant scope.")
    scope = require_profile_scope(
        user=request.user,
        tenant_id=tenant_id,
        profile_id=preview.profile_id,
        permission_code="executions.execute",
        minimum_level=ProfileAccessLevel.EXECUTE,
    )
    if preview.status != ActionPreviewStatus.APPROVED:
        raise ValidationError(
            {"status": ["Only APPROVED actions can receive execution results."]}
        )
    version = _current_version(preview)
    if ExecutionRecord.objects.filter(
        preview=preview,
        preview_version=version,
    ).exists():
        raise ValidationError(
            {"preview": ["This Action Preview version already has a result."]}
        )
    stored_evidence = _store_execution_evidence(
        tenant_id=scope.membership.tenant_id,
        evidence_file=evidence_file,
    )
    merged_evidence = dict(evidence_metadata)
    merged_evidence.update(stored_evidence)
    try:
        record = ExecutionRecord.objects.create(
            preview=preview,
            preview_version=version,
            outcome=outcome,
            actual_value=actual_value,
            executed_at=executed_at,
            note=note,
            evidence_metadata=merged_evidence,
            recorded_by=request.user,
            idempotency_key=idempotency_key,
        )
    except IntegrityError as exc:
        if stored_evidence:
            LocalFileStorage().delete(key=str(stored_evidence["storageKey"]))
        raise ValidationError(
            {"idempotency_key": ["Concurrent duplicate execution detected."]}
        ) from exc
    append_audit_log(
        request=request,
        tenant=scope.membership.tenant,
        actor=request.user,
        event="action_preview.execution_recorded",
        object_type="ActionPreview",
        object_id=preview.pk,
        after_data={
            "version": version.version_number,
            "outcome": outcome,
            "actual_value": actual_value,
            "executed_at": executed_at.isoformat(),
            "note": note,
        },
    )
    if outcome in {ExecutionOutcome.SUCCEEDED, ExecutionOutcome.SUCCESS}:
        from apps.actions.tasks import evaluate_effects

        transaction.on_commit(
            lambda: evaluate_effects.apply_async(args=[record.pk])
        )
    return preview, record


@transaction.atomic
def evaluate_execution(
    execution_record_id,
    *,
    observed: dict | None = None,
    evaluation_key: str | None = None,
) -> EffectEvaluation:
    record = (
        ExecutionRecord.objects.select_related(
            "preview",
            "preview_version",
        )
        .filter(pk=execution_record_id)
        .first()
    )
    if record is None:
        raise NotFound("Execution record does not exist.")
    observed_payload = dict(observed or {})
    key = evaluation_key or f"baseline:{record.pk}"
    existing = EffectEvaluation.objects.filter(idempotency_key=key).first()
    if existing is not None:
        if (
            existing.execution_record_id != record.pk
            or existing.result.get("observed", {}) != observed_payload
        ):
            raise ValidationError(
                {
                    "evaluation_key": [
                        "Key was already used for another effect evaluation."
                    ]
                }
            )
        return existing
    payload = record.preview_version.action_payload
    baseline = {
        "previewId": str(record.preview_id),
        "previewVersion": record.preview_version.version_number,
        "actionType": payload.get("actionType"),
        "objectType": payload.get("objectType"),
        "objectId": payload.get("objectId"),
        "beforeValue": payload.get("beforeValue", {}),
        "proposedValue": payload.get("afterValue", {}),
        "actualValue": record.actual_value,
        "executionOutcome": record.outcome,
        "executedAt": record.executed_at.isoformat(),
    }
    execution_date = record.executed_at.date()
    now = timezone.now()
    return EffectEvaluation.objects.create(
        execution_record=record,
        tenant=record.preview.tenant,
        profile=record.preview.profile,
        requested_by=record.recorded_by,
        status="OBSERVED" if observed_payload else "BASELINE_READY",
        baseline_start=execution_date - timedelta(days=7),
        baseline_end=execution_date - timedelta(days=1),
        observation_start=execution_date,
        observation_end=execution_date + timedelta(days=7),
        celery_task_id=f"effect-{hashlib.sha256(key.encode()).hexdigest()[:32]}",
        idempotency_key=key,
        result={"baseline": baseline, "observed": observed_payload},
        started_at=now,
        finished_at=now,
    )


@transaction.atomic
def evaluate_action_preview_effect(
    *,
    request,
    tenant_id,
    preview_id,
    execution_record_id,
    observed: dict,
    evaluation_key: str,
) -> EffectEvaluation:
    preview = (
        ActionPreview.objects.select_related("tenant", "profile")
        .filter(pk=preview_id, tenant_id=tenant_id)
        .first()
    )
    if preview is None:
        raise NotFound("Action Preview does not exist in the current tenant scope.")
    scope = require_profile_scope(
        user=request.user,
        tenant_id=tenant_id,
        profile_id=preview.profile_id,
        permission_code="executions.execute",
        minimum_level=ProfileAccessLevel.EXECUTE,
    )
    record = preview.execution_records.filter(pk=execution_record_id).first()
    if record is None:
        raise NotFound("Execution record does not exist in this Action Preview.")
    evaluation = evaluate_execution(
        record.pk,
        observed=observed,
        evaluation_key=evaluation_key,
    )
    append_audit_log(
        request=request,
        tenant=scope.membership.tenant,
        actor=request.user,
        event="action_preview.effect_evaluated",
        object_type="ActionPreview",
        object_id=preview.pk,
        after_data={
            "execution_record_id": str(record.pk),
            "evaluation_id": str(evaluation.pk),
            "status": evaluation.status,
        },
    )
    return evaluation
