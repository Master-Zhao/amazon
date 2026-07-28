import hashlib
import json
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import IntegrityError, transaction
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.serializers import ValidationError

from apps.actions.models import (
    ActionPreview,
    ActionPreviewStatus,
    ActionPreviewVersion,
    ApprovalDecision,
    ApprovalRecord,
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
            if target.state != expected_state:
                raise ValidationError(
                    {"before_value": ["Campaign state drift detected."]}
                )
            if proposed_state == expected_state:
                raise ValidationError({"after_value": ["State must change."]})
        return target

    if action_type in {
        ActionType.UPDATE_KEYWORD_BID,
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
            if target.state != expected_state:
                raise ValidationError(
                    {"before_value": ["Keyword state drift detected."]}
                )
            if proposed_state == expected_state:
                raise ValidationError({"after_value": ["State must change."]})
        return target

    if action_type in {
        ActionType.UPDATE_PRODUCT_TARGET_BID,
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
        if action_type == ActionType.UPDATE_PRODUCT_TARGET_BID:
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
            if target.state != expected_state:
                raise ValidationError(
                    {"before_value": ["Product Target state drift detected."]}
                )
            if proposed_state == expected_state:
                raise ValidationError({"after_value": ["State must change."]})
        return target

    if action_type == ActionType.CREATE_KEYWORD:
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

    if action_type == ActionType.CREATE_NEGATIVE_KEYWORD:
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
    if preview.status != ActionPreviewStatus.DRAFT:
        raise ValidationError(
            {"status": ["Only a DRAFT Action Preview can be submitted."]}
        )
    version = _current_version(preview)
    target = _validate_action_payload(
        payload=version.action_payload,
        profile_id=scope.profile.pk,
    )
    if _state_version(target) != version.object_state_version:
        raise ValidationError(
            {"before_value": ["Object state drift detected since preview creation."]}
        )
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
        before_data={"status": ActionPreviewStatus.DRAFT},
        after_data={
            "status": ActionPreviewStatus.PENDING_APPROVAL,
            "version": preview.current_version_number,
        },
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
    target = _validate_action_payload(
        payload=version.action_payload,
        profile_id=scope.profile.pk,
    )
    if _state_version(target) != version.object_state_version:
        raise ValidationError(
            {"before_value": ["Object state drift detected since preview creation."]}
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
    try:
        record = ExecutionRecord.objects.create(
            preview=preview,
            preview_version=version,
            outcome=outcome,
            actual_value=actual_value,
            executed_at=executed_at,
            note=note,
            evidence_metadata=evidence_metadata,
            recorded_by=request.user,
            idempotency_key=idempotency_key,
        )
    except IntegrityError as exc:
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
    return preview, record
