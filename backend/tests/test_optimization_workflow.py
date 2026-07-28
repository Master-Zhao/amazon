from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

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
from apps.actions.services import (
    create_preview,
    decide_preview,
    evaluate_execution,
    record_execution,
    submit_preview,
)
from apps.advertising.models import (
    AdGroup,
    Campaign,
    EntityState,
    Keyword,
    MatchType,
    ProductTarget,
)
from apps.agents.agent_definitions import DataAnalysisAgent
from apps.agents.models import AgentRun, AgentTaskStatus
from apps.agents.services import create_analysis
from apps.analytics.models import CampaignDailyMetric
from apps.audit.models import AuditLog
from apps.recommendations.models import Recommendation
from apps.recommendations.services import validate_recommendation
from apps.reports.models import (
    ImportBatch,
    ImportStatus,
    ImportTask,
    ReportType,
    ReportUpload,
)
from apps.stores.models import (
    AdvertisingProfile,
    AmazonStore,
    Marketplace,
    StoreMarketplace,
)
from apps.tenants.models import MembershipRole, Tenant, TenantMembership, TenantType
from integrations.llm.providers import ExternalLLMProviderBoundary
from integrations.storage.base import StoredFile


def request_for(user, request_id="req_workflow"):
    return SimpleNamespace(user=user, request_id=request_id)


@pytest.fixture
def workflow_context(db):
    user_model = get_user_model()
    owner = user_model.objects.create_user(
        username="workflow-owner",
        email="workflow-owner@example.invalid",
        password="password",
    )
    tenant = Tenant.objects.create(
        name="Workflow", tenant_type=TenantType.PERSONAL, target_acos="0.25"
    )
    TenantMembership.objects.create(
        tenant=tenant, user=owner, role=MembershipRole.OWNER
    )
    marketplace = Marketplace.objects.create(
        code="US",
        name="Amazon.com",
        country_code="US",
        currency="USD",
        timezone="America/Los_Angeles",
    )
    store = AmazonStore.objects.create(
        tenant=tenant, name="Store", external_store_id="WORKFLOW-STORE"
    )
    scope = StoreMarketplace.objects.create(
        store=store, marketplace=marketplace, seller_id="SELLER"
    )
    profile = AdvertisingProfile.objects.create(
        store_marketplace=scope,
        external_profile_id="WORKFLOW-PROFILE",
        name="Profile",
        currency="USD",
        timezone=marketplace.timezone,
    )
    campaign = Campaign.objects.create(
        profile=profile,
        external_campaign_id="WORKFLOW-CAMPAIGN",
        name="Campaign",
        state=EntityState.ENABLED,
        daily_budget="50.00",
        currency="USD",
    )
    upload = ReportUpload.objects.create(
        tenant=tenant,
        profile=profile,
        report_type=ReportType.CAMPAIGN,
        original_name="fixture.csv",
        content_type="text/csv",
        size_bytes=1,
        sha256="b" * 64,
        storage_path="reports/fixture.csv",
        uploaded_by=owner,
    )
    import_task = ImportTask.objects.create(
        upload=upload,
        status=ImportStatus.SUCCEEDED,
        requested_by=owner,
        idempotency_key="workflow-import",
    )
    batch = ImportBatch.objects.create(
        task=import_task, status=ImportStatus.SUCCEEDED
    )
    CampaignDailyMetric.objects.create(
        campaign=campaign,
        business_date=date(2026, 7, 20),
        impressions=1000,
        clicks=50,
        spend="100",
        orders=5,
        sales="250",
        ctr="0.05",
        cpc="2",
        cvr="0.1",
        acos="0.4",
        roas="2.5",
        invalid_reasons={},
        currency="USD",
        source_batch=batch,
        budget_snapshot="50.00",
        state_snapshot=EntityState.ENABLED,
    )
    return owner, tenant, profile


@pytest.mark.django_db(transaction=True)
def test_mock_four_agent_analysis_creates_valid_recommendation(workflow_context):
    owner, tenant, profile = workflow_context

    task = create_analysis(
        user=owner,
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        idempotency_key="analysis-1",
    )
    task.refresh_from_db()

    assert task.status == AgentTaskStatus.SUCCEEDED
    assert AgentRun.objects.filter(task=task).count() == 4
    recommendation = Recommendation.objects.get(analysis_task=task)
    assert recommendation.action_type == "UPDATE_CAMPAIGN_BUDGET"
    assert recommendation.risk_level == "LOW"
    assert ExternalLLMProviderBoundary.capability["mode"] == "reserved"


class InvalidProvider:
    def generate(self, **kwargs):
        return {"schemaVersion": "bad"}


def test_invalid_agent_schema_is_rejected():
    with pytest.raises(ValueError):
        DataAnalysisAgent(InvalidProvider()).run({"runId": "run"})


@pytest.mark.django_db(transaction=True)
def test_personal_owner_approval_execution_and_audit_are_append_only(workflow_context):
    owner, tenant, profile = workflow_context
    analysis = create_analysis(
        user=owner,
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        idempotency_key="analysis-preview",
    )
    recommendation = Recommendation.objects.get(analysis_task=analysis)
    request = request_for(owner)

    preview = create_preview(
        request=request,
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        recommendation_ids=[recommendation.pk],
    )
    submit_preview(request=request, preview_id=preview.pk)
    approved = decide_preview(
        request=request,
        preview_id=preview.pk,
        decision=PreviewStatus.APPROVED,
        comment="个人 Owner 自确认",
        idempotency_key="approve-1",
    )
    item = ExecutionItem.objects.get(task=approved.execution_task)
    first = record_execution(
        request=request,
        item_id=item.pk,
        result="SUCCEEDED",
        actual_value={"budget": "55.00"},
        executed_at=timezone.now(),
        note="已在 Amazon 后台人工执行",
        idempotency_key="execute-1",
    )
    repeated = record_execution(
        request=request,
        item_id=item.pk,
        result="SUCCEEDED",
        actual_value={"budget": "55.00"},
        executed_at=timezone.now(),
        note="重复请求",
        idempotency_key="execute-1",
    )

    assert approved.status == PreviewStatus.APPROVED
    assert ActionPreviewVersion.objects.get(preview=preview).frozen_at is not None
    frozen = ActionPreviewVersion.objects.get(preview=preview)
    frozen.items = []
    with pytest.raises(RuntimeError):
        frozen.save()
    assert first.pk == repeated.pk
    assert AuditLog.objects.filter(tenant=tenant).count() >= 4
    with pytest.raises(RuntimeError):
        AuditLog.objects.first().delete()
    with pytest.raises(RuntimeError):
        AuditLog.objects.filter(tenant=tenant).delete()


@pytest.mark.django_db(transaction=True)
def test_preview_submit_and_approval_retries_are_idempotent(workflow_context):
    owner, tenant, profile = workflow_context
    analysis = create_analysis(
        user=owner,
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        idempotency_key="analysis-idempotency",
    )
    recommendation = Recommendation.objects.get(analysis_task=analysis)
    request = request_for(owner)

    first = create_preview(
        request=request,
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        recommendation_ids=[recommendation.pk],
        idempotency_key="preview-idempotency",
    )
    repeated = create_preview(
        request=request,
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        recommendation_ids=[recommendation.pk],
        idempotency_key="preview-idempotency",
    )
    first_submit = submit_preview(request=request, preview_id=first.pk)
    repeated_submit = submit_preview(request=request, preview_id=first.pk)
    first_approval = decide_preview(
        request=request,
        preview_id=first.pk,
        decision=PreviewStatus.APPROVED,
        comment="approved",
        idempotency_key="approval-idempotency",
    )
    repeated_approval = decide_preview(
        request=request,
        preview_id=first.pk,
        decision=PreviewStatus.APPROVED,
        comment="approved",
        idempotency_key="approval-idempotency",
    )

    assert repeated.pk == first.pk
    assert repeated_submit.pk == first_submit.pk
    assert repeated_approval.pk == first_approval.pk
    assert ActionPreview.objects.filter(tenant=tenant).count() == 1
    assert ApprovalRecord.objects.filter(preview=first).count() == 1
    assert ExecutionTask.objects.filter(preview=first).count() == 1


@pytest.mark.django_db(transaction=True)
def test_returned_preview_creates_and_freezes_a_new_version(workflow_context):
    owner, tenant, profile = workflow_context
    analysis = create_analysis(
        user=owner,
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        idempotency_key="analysis-return",
    )
    preview = create_preview(
        request=request_for(owner),
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        recommendation_ids=[Recommendation.objects.get(analysis_task=analysis).pk],
    )
    submit_preview(request=request_for(owner), preview_id=preview.pk)

    returned = decide_preview(
        request=request_for(owner),
        preview_id=preview.pk,
        decision=PreviewStatus.RETURNED,
        comment="revise",
        idempotency_key="return-1",
    )
    versions = list(returned.versions.order_by("version"))

    assert returned.status == PreviewStatus.RETURNED
    assert returned.current_version == 2
    assert versions[0].frozen_at is not None
    assert versions[1].frozen_at is None
    resubmitted = submit_preview(request=request_for(owner), preview_id=preview.pk)
    versions[1].refresh_from_db()
    assert resubmitted.status == PreviewStatus.PENDING_APPROVAL
    assert versions[1].frozen_at is not None


@pytest.mark.django_db(transaction=True)
def test_execution_evidence_effect_evaluation_and_records_are_append_only(
    workflow_context,
):
    owner, tenant, profile = workflow_context
    analysis = create_analysis(
        user=owner,
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        idempotency_key="analysis-evidence",
    )
    preview = create_preview(
        request=request_for(owner),
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        recommendation_ids=[Recommendation.objects.get(analysis_task=analysis).pk],
    )
    submit_preview(request=request_for(owner), preview_id=preview.pk)
    approved = decide_preview(
        request=request_for(owner),
        preview_id=preview.pk,
        decision=PreviewStatus.APPROVED,
        comment="approved",
        idempotency_key="approve-evidence",
    )
    item = ExecutionItem.objects.get(task=approved.execution_task)
    evidence = SimpleUploadedFile("proof.txt", b"manual execution evidence")
    with patch(
        "apps.actions.services.LocalFileStorage.save_stream",
        return_value=StoredFile(
            "execution-evidence/proof.txt",
            len(b"manual execution evidence"),
            "a" * 64,
        ),
    ) as save_stream:
        record = record_execution(
            request=request_for(owner),
            item_id=item.pk,
            result="SUCCEEDED",
            actual_value={"budget": "55.00"},
            executed_at=timezone.now(),
            note="with evidence",
            idempotency_key="execute-evidence",
            evidence_file=evidence,
        )
    assert record.evidence_path == "execution-evidence/proof.txt"
    save_stream.assert_called_once()
    with pytest.raises(Exception) as duplicate_error:
        record_execution(
            request=request_for(owner),
            item_id=item.pk,
            result="SUCCEEDED",
            actual_value={"budget": "56.00"},
            executed_at=timezone.now(),
            note="different retry key",
            idempotency_key="execute-evidence-second-key",
        )
    assert getattr(duplicate_error.value, "status_code", None) == 400

    evaluation = EffectEvaluation.objects.get(execution_task=approved.execution_task)
    repeated = evaluate_execution(approved.execution_task.pk)
    assert repeated.pk == evaluation.pk
    assert evaluation.status == "BASELINE_READY"
    assert evaluation.baseline["completedItemCount"] == 1

    record.note = "mutated"
    with pytest.raises(RuntimeError):
        record.save()
    with pytest.raises(RuntimeError):
        ExecutionRecord.objects.filter(pk=record.pk).update(note="mutated")
    approval = ApprovalRecord.objects.get(preview=preview)
    approval.comment = "mutated"
    with pytest.raises(RuntimeError):
        approval.save()
    with pytest.raises(RuntimeError):
        ApprovalRecord.objects.filter(pk=approval.pk).delete()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "action_type",
    [
        "UPDATE_CAMPAIGN_BUDGET",
        "ENABLE_CAMPAIGN",
        "PAUSE_CAMPAIGN",
        "UPDATE_KEYWORD_BID",
        "ENABLE_KEYWORD",
        "PAUSE_KEYWORD",
        "UPDATE_TARGET_BID",
        "ENABLE_TARGET",
        "PAUSE_TARGET",
        "ADD_KEYWORD",
        "ADD_NEGATIVE_KEYWORD",
    ],
)
def test_all_eleven_action_types_have_deterministic_validation(
    workflow_context, action_type
):
    _, _, profile = workflow_context
    campaign = Campaign.objects.get(profile=profile)
    ad_group = AdGroup.objects.create(
        campaign=campaign,
        external_ad_group_id="GROUP-1",
        name="Group",
        state=EntityState.ENABLED,
    )
    keyword = Keyword.objects.create(
        ad_group=ad_group,
        external_keyword_id="KEYWORD-1",
        text="shoe",
        match_type=MatchType.EXACT,
        state=EntityState.ENABLED,
        bid="1.00",
    )
    target = ProductTarget.objects.create(
        ad_group=ad_group,
        external_target_id="TARGET-1",
        expression="asin=EXAMPLE",
        state=EntityState.ENABLED,
        bid="2.00",
    )
    item = {
        "actionType": action_type,
        "objectType": "CAMPAIGN",
        "objectId": str(campaign.pk),
        "beforeValue": {},
        "afterValue": {},
        "reason": "deterministic test",
        "evidence": [],
        "riskLevel": "LOW",
    }
    if action_type == "UPDATE_CAMPAIGN_BUDGET":
        item["beforeValue"] = {"budget": "50.00"}
        item["afterValue"] = {"budget": "55.00"}
    elif action_type in {"ENABLE_CAMPAIGN", "PAUSE_CAMPAIGN"}:
        target_state = (
            EntityState.ENABLED
            if action_type == "ENABLE_CAMPAIGN"
            else EntityState.PAUSED
        )
        campaign.state = (
            EntityState.PAUSED
            if target_state == EntityState.ENABLED
            else EntityState.ENABLED
        )
        campaign.save(update_fields=["state"])
        item["beforeValue"] = {"state": campaign.state}
        item["afterValue"] = {"state": target_state}
    elif action_type in {
        "UPDATE_KEYWORD_BID",
        "ENABLE_KEYWORD",
        "PAUSE_KEYWORD",
    }:
        item["objectType"] = "KEYWORD"
        item["objectId"] = str(keyword.pk)
        if action_type == "UPDATE_KEYWORD_BID":
            item["beforeValue"] = {"bid": "1.00"}
            item["afterValue"] = {"bid": "1.20"}
        else:
            target_state = (
                EntityState.ENABLED
                if action_type == "ENABLE_KEYWORD"
                else EntityState.PAUSED
            )
            keyword.state = (
                EntityState.PAUSED
                if target_state == EntityState.ENABLED
                else EntityState.ENABLED
            )
            keyword.save(update_fields=["state"])
            item["beforeValue"] = {"state": keyword.state}
            item["afterValue"] = {"state": target_state}
    elif "TARGET" in action_type:
        item["objectType"] = "PRODUCT_TARGET"
        item["objectId"] = str(target.pk)
        if action_type == "UPDATE_TARGET_BID":
            item["beforeValue"] = {"bid": "2.00"}
            item["afterValue"] = {"bid": "2.20"}
        else:
            target_state = (
                EntityState.ENABLED
                if action_type == "ENABLE_TARGET"
                else EntityState.PAUSED
            )
            target.state = (
                EntityState.PAUSED
                if target_state == EntityState.ENABLED
                else EntityState.ENABLED
            )
            target.save(update_fields=["state"])
            item["beforeValue"] = {"state": target.state}
            item["afterValue"] = {"state": target_state}
    elif action_type == "ADD_KEYWORD":
        item["objectType"] = "AD_GROUP"
        item["objectId"] = str(ad_group.pk)
        item["afterValue"] = {
            "text": "new keyword",
            "matchType": MatchType.PHRASE,
            "bid": "1.50",
        }
    else:
        item["afterValue"] = {
            "text": "irrelevant",
            "matchType": MatchType.EXACT,
        }

    assert validate_recommendation(
        task=SimpleNamespace(profile=profile),
        item=item,
    ) == item


@pytest.mark.django_db(transaction=True)
def test_team_submitter_cannot_approve_self(workflow_context):
    owner, tenant, profile = workflow_context
    tenant.tenant_type = TenantType.TEAM
    tenant.save(update_fields=["tenant_type"])
    analysis = create_analysis(
        user=owner,
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        idempotency_key="analysis-team",
    )
    preview = create_preview(
        request=request_for(owner),
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        recommendation_ids=[Recommendation.objects.get(analysis_task=analysis).pk],
    )
    submit_preview(request=request_for(owner), preview_id=preview.pk)

    with pytest.raises(Exception) as error:
        decide_preview(
            request=request_for(owner),
            preview_id=preview.pk,
            decision=PreviewStatus.APPROVED,
            comment="invalid self approval",
            idempotency_key="self-approve",
        )
    assert getattr(error.value, "status_code", None) == 403


@pytest.mark.django_db(transaction=True)
def test_json_api_contract_runs_analysis_approval_execution_and_audit(workflow_context):
    owner, tenant, profile = workflow_context
    client = APIClient()
    client.force_authenticate(owner)
    tenant_headers = {"HTTP_X_TENANT_ID": str(tenant.pk)}

    analysis = client.post(
        "/api/v1/analysis/tasks",
        {"tenantId": str(tenant.pk), "profileId": str(profile.pk)},
        format="json",
        HTTP_IDEMPOTENCY_KEY="api-analysis",
        **tenant_headers,
    )
    assert analysis.status_code == 202
    task_id = analysis.json()["data"]["taskId"]

    task = client.get(f"/api/v1/analysis/tasks/{task_id}", **tenant_headers)
    recommendations = client.get(
        f"/api/v1/recommendations/?profileId={profile.pk}", **tenant_headers
    )
    recommendation_id = recommendations.json()["data"]["items"][0]["id"]
    assert recommendations.json()["data"]["pagination"]["total"] == 1
    assert task.json()["data"]["status"] == "SUCCEEDED"

    created = client.post(
        "/api/v1/actions/previews",
        {
            "tenantId": str(tenant.pk),
            "profileId": str(profile.pk),
            "recommendationIds": [recommendation_id],
        },
        format="json",
        **tenant_headers,
    )
    preview_id = created.json()["data"]["previewId"]
    assert created.status_code == 201
    assert client.post(
        f"/api/v1/actions/previews/{preview_id}/submit", **tenant_headers
    ).status_code == 200
    assert client.post(
        f"/api/v1/actions/previews/{preview_id}/decisions",
        {"decision": "APPROVED", "comment": "API contract"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="api-approval",
        **tenant_headers,
    ).status_code == 200

    previews = client.get(
        f"/api/v1/actions/previews?profileId={profile.pk}", **tenant_headers
    )
    execution_item = previews.json()["data"]["items"][0]["execution"]["items"][0]
    recorded = client.post(
        f"/api/v1/actions/execution-items/{execution_item['id']}/records",
        {
            "result": "SUCCEEDED",
            "actualValue": {"budget": "55.00"},
            "executedAt": timezone.now().isoformat(),
            "note": "API integration",
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY="api-execution",
        **tenant_headers,
    )
    audit = client.get("/api/v1/audit/", **tenant_headers)

    assert recorded.status_code == 201
    assert any(
        item["event"] == "EXECUTION_RECORDED"
        for item in audit.json()["data"]["items"]
    )
