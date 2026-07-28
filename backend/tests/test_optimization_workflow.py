from datetime import date
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.actions.models import ActionPreviewVersion, ExecutionItem, PreviewStatus
from apps.actions.services import (
    create_preview,
    decide_preview,
    record_execution,
    submit_preview,
)
from apps.advertising.models import Campaign, EntityState
from apps.agents.agent_definitions import DataAnalysisAgent
from apps.agents.models import AgentRun, AgentTaskStatus
from apps.agents.services import create_analysis
from apps.analytics.models import CampaignDailyMetric
from apps.audit.models import AuditLog
from apps.recommendations.models import Recommendation
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
