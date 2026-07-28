from types import SimpleNamespace

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.actions.models import (
    ActionPreviewStatus,
    ActionPreviewVersion,
    ApprovalDecision,
    ApprovalRecord,
    EffectEvaluation,
    ExecutionOutcome,
    ExecutionRecord,
)
from apps.actions.services import (
    create_action_preview,
    create_returned_preview_version,
    decide_action_preview,
    evaluate_action_preview_effect,
    record_manual_execution,
    submit_action_preview,
    validate_action_payload,
    withdraw_action_preview,
)
from apps.advertising.models import (
    AdGroup,
    Campaign,
    EntityState,
    Keyword,
    MatchType,
    ProductTarget,
)
from apps.agents.models import AgentRun, AgentRunStatus
from apps.audit.models import AuditLog
from apps.recommendations.models import (
    ActionType,
    Recommendation,
    RecommendationRevision,
)
from apps.stores.models import (
    AdvertisingProfile,
    AmazonStore,
    Marketplace,
    StoreMarketplace,
)
from apps.tenants.models import (
    MembershipRole,
    Tenant,
    TenantMembership,
    TenantType,
)


pytestmark = pytest.mark.django_db


def request_for(user, request_id="req-workflow"):
    return SimpleNamespace(user=user, request_id=request_id)


def build_workflow(*, tenant_type=TenantType.PERSONAL):
    owner = User.objects.create_user(
        username=f"owner-{tenant_type.lower()}",
        email=f"owner-{tenant_type.lower()}@example.invalid",
        password="test-only-password",
    )
    reviewer = User.objects.create_user(
        username=f"reviewer-{tenant_type.lower()}",
        email=f"reviewer-{tenant_type.lower()}@example.invalid",
        password="test-only-password",
    )
    tenant = Tenant.objects.create(
        name=f"{tenant_type} workflow",
        tenant_type=tenant_type,
        target_acos="0.2500",
    )
    TenantMembership.objects.create(
        tenant=tenant,
        user=owner,
        membership_role=MembershipRole.OWNER,
    )
    TenantMembership.objects.create(
        tenant=tenant,
        user=reviewer,
        membership_role=MembershipRole.ADMIN,
    )
    marketplace = Marketplace.objects.create(
        code=f"WF-{tenant.pk}",
        name="Workflow Marketplace",
        currency_code="USD",
        timezone="UTC",
    )
    store = AmazonStore.objects.create(
        tenant=tenant,
        name="Workflow Store",
        external_store_id=f"workflow-store-{tenant.pk}",
    )
    store_marketplace = StoreMarketplace.objects.create(
        store=store,
        marketplace=marketplace,
    )
    profile = AdvertisingProfile.objects.create(
        store_marketplace=store_marketplace,
        external_profile_id=f"workflow-profile-{tenant.pk}",
        name="Workflow Profile",
        currency_code="USD",
        timezone="UTC",
    )
    campaign = Campaign.objects.create(
        profile=profile,
        external_campaign_id=f"workflow-campaign-{tenant.pk}",
        name="Workflow Campaign",
        state=EntityState.ENABLED,
        daily_budget="50.0000",
        currency_code="USD",
    )
    ad_group = AdGroup.objects.create(
        campaign=campaign,
        external_ad_group_id="workflow-ad-group",
        name="Workflow Ad Group",
        state=EntityState.ENABLED,
    )
    keyword = Keyword.objects.create(
        ad_group=ad_group,
        external_keyword_id="workflow-keyword",
        keyword_text="running shoes",
        match_type=MatchType.EXACT,
        state=EntityState.ENABLED,
        bid="1.2500",
    )
    target = ProductTarget.objects.create(
        ad_group=ad_group,
        external_target_id="workflow-target",
        expression="asin=DEMO",
        state=EntityState.ENABLED,
        bid="0.8500",
    )
    agent_run = AgentRun.objects.create(
        tenant=tenant,
        profile=profile,
        status=AgentRunStatus.SUCCEEDED,
        celery_task_id=f"workflow-run-{tenant.pk}",
        requested_by=owner,
    )
    recommendation = Recommendation.objects.create(
        tenant=tenant,
        profile=profile,
        campaign=campaign,
        agent_run=agent_run,
        action_type=ActionType.UPDATE_CAMPAIGN_BUDGET,
    )
    revision = RecommendationRevision.objects.create(
        recommendation=recommendation,
        revision_number=1,
        schema_version="agent-result-v1",
        action_type=ActionType.UPDATE_CAMPAIGN_BUDGET,
        object_type="Campaign",
        object_id=str(campaign.pk),
        before_value={"dailyBudget": "50.0000", "currency": "USD"},
        after_value={"dailyBudget": "45.0000", "currency": "USD"},
        reason="High ACOS requires human review.",
        evidence=[{"ruleCode": "HIGH_ACOS"}],
        risk_level="MEDIUM",
    )
    return SimpleNamespace(
        owner=owner,
        reviewer=reviewer,
        tenant=tenant,
        profile=profile,
        campaign=campaign,
        ad_group=ad_group,
        keyword=keyword,
        target=target,
        recommendation=recommendation,
        revision=revision,
        agent_run=agent_run,
    )


def create_preview(context):
    return create_action_preview(
        request=request_for(context.owner),
        tenant_id=context.tenant.pk,
        recommendation_id=context.recommendation.pk,
    )


def test_personal_owner_self_approval_execution_evidence_and_effect(settings):
    settings.REPORT_STORAGE_ROOT = (
        settings.BASE_DIR / "test-artifacts" / "action-evidence"
    )
    context = build_workflow()
    preview = create_preview(context)
    submit_action_preview(
        request=request_for(context.owner),
        tenant_id=context.tenant.pk,
        preview_id=preview.pk,
    )
    approved, approval = decide_action_preview(
        request=request_for(context.owner),
        tenant_id=context.tenant.pk,
        preview_id=preview.pk,
        decision=ApprovalDecision.APPROVED,
        comment="Personal owner confirmation.",
        idempotency_key="personal-approval",
    )
    executed, record = record_manual_execution(
        request=request_for(context.owner),
        tenant_id=context.tenant.pk,
        preview_id=preview.pk,
        outcome=ExecutionOutcome.SUCCEEDED,
        actual_value={"dailyBudget": "45.0000", "currency": "USD"},
        executed_at=timezone.now(),
        note="Updated in Amazon console.",
        evidence_metadata={"reference": "manual-console"},
        evidence_file=SimpleUploadedFile(
            "proof.txt",
            b"fictional execution evidence",
            content_type="text/plain",
        ),
        idempotency_key="personal-execution",
    )
    evaluation = evaluate_action_preview_effect(
        request=request_for(context.owner),
        tenant_id=context.tenant.pk,
        preview_id=preview.pk,
        execution_record_id=record.pk,
        observed={"acos": "0.2200", "windowDays": 7},
        evaluation_key="personal-effect-observed",
    )

    assert approved.status == ActionPreviewStatus.APPROVED
    assert executed.status == ActionPreviewStatus.APPROVED
    assert approval.preview_version.version_number == 1
    assert record.evidence_metadata["originalFilename"] == "proof.txt"
    assert len(record.evidence_metadata["sha256"]) == 64
    assert evaluation.status == "OBSERVED"
    assert evaluation.result["baseline"]["beforeValue"]["dailyBudget"] == "50.0000"
    assert evaluation.result["observed"]["acos"] == "0.2200"
    assert ApprovalRecord.objects.count() == 1
    assert ExecutionRecord.objects.count() == 1
    assert EffectEvaluation.objects.count() == 1
    with pytest.raises(TypeError, match="append-only"):
        approval.save()
    assert AuditLog.objects.filter(
        event="action_preview.effect_evaluated",
        object_id=str(preview.pk),
    ).exists()


def test_team_submitter_cannot_self_approve_but_admin_can():
    context = build_workflow(tenant_type=TenantType.TEAM)
    preview = create_preview(context)
    submit_action_preview(
        request=request_for(context.owner),
        tenant_id=context.tenant.pk,
        preview_id=preview.pk,
    )

    with pytest.raises(PermissionDenied):
        decide_action_preview(
            request=request_for(context.owner),
            tenant_id=context.tenant.pk,
            preview_id=preview.pk,
            decision=ApprovalDecision.APPROVED,
            comment="Forbidden self approval.",
            idempotency_key="team-self-approval",
        )

    approved, _ = decide_action_preview(
        request=request_for(context.reviewer),
        tenant_id=context.tenant.pk,
        preview_id=preview.pk,
        decision=ApprovalDecision.APPROVED,
        comment="Independent approval.",
        idempotency_key="team-admin-approval",
    )
    assert approved.status == ActionPreviewStatus.APPROVED


def test_returned_requires_new_immutable_version_before_resubmit():
    context = build_workflow(tenant_type=TenantType.TEAM)
    preview = create_preview(context)
    submit_action_preview(
        request=request_for(context.owner),
        tenant_id=context.tenant.pk,
        preview_id=preview.pk,
    )
    returned, _ = decide_action_preview(
        request=request_for(context.reviewer),
        tenant_id=context.tenant.pk,
        preview_id=preview.pk,
        decision=ApprovalDecision.RETURNED,
        comment="Reduce the proposed budget change.",
        idempotency_key="return-preview",
    )
    with pytest.raises(Exception, match="new immutable version"):
        submit_action_preview(
            request=request_for(context.owner),
            tenant_id=context.tenant.pk,
            preview_id=preview.pk,
        )

    payload = dict(returned.versions.get(version_number=1).action_payload)
    payload["afterValue"] = {"dailyBudget": "47.5000", "currency": "USD"}
    revised = create_returned_preview_version(
        request=request_for(context.owner),
        tenant_id=context.tenant.pk,
        preview_id=preview.pk,
        action_payload=payload,
    )
    resubmitted = submit_action_preview(
        request=request_for(context.owner),
        tenant_id=context.tenant.pk,
        preview_id=preview.pk,
    )

    assert revised.current_version_number == 2
    assert resubmitted.status == ActionPreviewStatus.PENDING_APPROVAL
    assert list(
        ActionPreviewVersion.objects.filter(preview=preview).values_list(
            "version_number",
            flat=True,
        )
    ) == [1, 2]


def test_creator_can_withdraw_pending_preview_idempotently():
    context = build_workflow()
    preview = create_preview(context)
    submit_action_preview(
        request=request_for(context.owner),
        tenant_id=context.tenant.pk,
        preview_id=preview.pk,
    )
    withdrawn = withdraw_action_preview(
        request=request_for(context.owner),
        tenant_id=context.tenant.pk,
        preview_id=preview.pk,
    )
    repeated = withdraw_action_preview(
        request=request_for(context.owner),
        tenant_id=context.tenant.pk,
        preview_id=preview.pk,
    )
    assert withdrawn.status == repeated.status == ActionPreviewStatus.WITHDRAWN
    assert AuditLog.objects.filter(event="action_preview.withdrawn").count() == 1


def test_all_eleven_v1_action_payloads_validate_against_profile_state():
    context = build_workflow()
    base = {
        "schemaVersion": "agent-result-v1",
        "reason": "Deterministic validation test.",
        "evidence": [],
        "riskLevel": "LOW",
    }
    payloads = [
        {
            **base,
            "actionType": ActionType.UPDATE_CAMPAIGN_BUDGET,
            "objectType": "Campaign",
            "objectId": str(context.campaign.pk),
            "beforeValue": {"dailyBudget": "50.0000", "currency": "USD"},
            "afterValue": {"dailyBudget": "45.0000", "currency": "USD"},
        },
        {
            **base,
            "actionType": ActionType.PAUSE_CAMPAIGN,
            "objectType": "Campaign",
            "objectId": str(context.campaign.pk),
            "beforeValue": {"state": "ENABLED"},
            "afterValue": {"state": "PAUSED"},
        },
        {
            **base,
            "actionType": ActionType.UPDATE_KEYWORD_BID,
            "objectType": "Keyword",
            "objectId": str(context.keyword.pk),
            "beforeValue": {"bid": "1.2500", "currency": "USD"},
            "afterValue": {"bid": "1.1000", "currency": "USD"},
        },
        {
            **base,
            "actionType": ActionType.PAUSE_KEYWORD,
            "objectType": "Keyword",
            "objectId": str(context.keyword.pk),
            "beforeValue": {"state": "ENABLED"},
            "afterValue": {"state": "PAUSED"},
        },
        {
            **base,
            "actionType": ActionType.UPDATE_TARGET_BID,
            "objectType": "ProductTarget",
            "objectId": str(context.target.pk),
            "beforeValue": {"bid": "0.8500", "currency": "USD"},
            "afterValue": {"bid": "0.7500", "currency": "USD"},
        },
        {
            **base,
            "actionType": ActionType.PAUSE_TARGET,
            "objectType": "ProductTarget",
            "objectId": str(context.target.pk),
            "beforeValue": {"state": "ENABLED"},
            "afterValue": {"state": "PAUSED"},
        },
        {
            **base,
            "actionType": ActionType.ADD_KEYWORD,
            "objectType": "AdGroup",
            "objectId": str(context.ad_group.pk),
            "beforeValue": {},
            "afterValue": {
                "keywordText": "trail shoes",
                "matchType": "EXACT",
                "bid": "1.0000",
                "currency": "USD",
            },
        },
        {
            **base,
            "actionType": ActionType.ADD_NEGATIVE_KEYWORD,
            "objectType": "Campaign",
            "objectId": str(context.campaign.pk),
            "beforeValue": {},
            "afterValue": {
                "negativeScope": "CAMPAIGN",
                "keywordText": "free",
                "matchType": "PHRASE",
            },
        },
    ]
    for payload in payloads:
        validate_action_payload(payload=payload, profile_id=context.profile.pk)

    context.campaign.state = EntityState.PAUSED
    context.campaign.save(update_fields=["state"])
    context.keyword.state = EntityState.PAUSED
    context.keyword.save(update_fields=["state"])
    context.target.state = EntityState.PAUSED
    context.target.save(update_fields=["state"])
    enable_payloads = [
        {
            **base,
            "actionType": ActionType.ENABLE_CAMPAIGN,
            "objectType": "Campaign",
            "objectId": str(context.campaign.pk),
            "beforeValue": {"state": "PAUSED"},
            "afterValue": {"state": "ENABLED"},
        },
        {
            **base,
            "actionType": ActionType.ENABLE_KEYWORD,
            "objectType": "Keyword",
            "objectId": str(context.keyword.pk),
            "beforeValue": {"state": "PAUSED"},
            "afterValue": {"state": "ENABLED"},
        },
        {
            **base,
            "actionType": ActionType.ENABLE_TARGET,
            "objectType": "ProductTarget",
            "objectId": str(context.target.pk),
            "beforeValue": {"state": "PAUSED"},
            "afterValue": {"state": "ENABLED"},
        },
    ]
    for payload in enable_payloads:
        validate_action_payload(payload=payload, profile_id=context.profile.pk)
    assert len(payloads) + len(enable_payloads) == 11


def test_action_transition_apis_are_real_and_camel_case():
    context = build_workflow(tenant_type=TenantType.TEAM)
    owner_client = APIClient()
    owner_client.force_authenticate(context.owner)
    reviewer_client = APIClient()
    reviewer_client.force_authenticate(context.reviewer)

    created = owner_client.post(
        f"/api/v1/actions/tenants/{context.tenant.pk}/recommendations/"
        f"{context.recommendation.pk}/previews",
    )
    preview_id = created.data["data"]["id"]
    submitted = owner_client.post(
        f"/api/v1/actions/tenants/{context.tenant.pk}/previews/"
        f"{preview_id}/submit",
    )
    returned = reviewer_client.post(
        f"/api/v1/actions/tenants/{context.tenant.pk}/previews/"
        f"{preview_id}/decision",
        {
            "decision": "RETURNED",
            "comment": "API return.",
            "idempotencyKey": "api-return",
        },
        format="json",
    )
    payload = returned.json()["data"]["currentVersion"]["actionPayload"]
    payload["afterValue"]["dailyBudget"] = "47.5000"
    versioned = owner_client.post(
        f"/api/v1/actions/tenants/{context.tenant.pk}/previews/"
        f"{preview_id}/versions",
        {"actionPayload": payload},
        format="json",
    )

    assert created.status_code == 201
    assert submitted.status_code == 200
    assert returned.status_code == 200
    assert versioned.status_code == 201
    assert versioned.json()["data"]["currentVersionNumber"] == 2
