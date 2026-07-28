import uuid

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound

from apps.agents.agent_definitions import (
    AnomalyDiagnosisAgent,
    BudgetAnalysisAgent,
    DataAnalysisAgent,
    StrategyAgent,
)
from apps.agents.models import AgentRun, AgentTaskStatus, AnalysisTask
from apps.analytics.selectors import dashboard
from apps.permissions.services import authorize
from apps.recommendations.services import persist_recommendations
from apps.stores.models import AdvertisingProfile
from integrations.llm.providers import MockLLMProvider


@transaction.atomic
def create_analysis(*, user, tenant_id, profile_id, idempotency_key):
    try:
        profile = AdvertisingProfile.objects.select_related(
            "store_marketplace__store__tenant"
        ).get(pk=profile_id)
    except (AdvertisingProfile.DoesNotExist, ValueError) as exc:
        raise NotFound("广告 Profile 不存在") from exc
    authorize(
        user=user,
        tenant_id=tenant_id,
        permission_code="analysis.run",
        profile=profile,
    )
    task, created = AnalysisTask.objects.get_or_create(
        tenant_id=tenant_id,
        idempotency_key=idempotency_key or uuid.uuid4().hex,
        defaults={
            "profile": profile,
            "status": AgentTaskStatus.QUEUED,
            "requested_by": user,
            "scope_snapshot": {
                "tenantId": str(tenant_id),
                "profileId": str(profile_id),
            },
        },
    )
    if created:
        from apps.agents.tasks import run_analysis_task

        transaction.on_commit(lambda: run_analysis_task.delay(str(task.pk)))
    return task


def run_orchestrator(task_id):
    with transaction.atomic():
        task = AnalysisTask.objects.select_for_update().select_related(
            "tenant", "profile", "requested_by"
        ).get(pk=task_id)
        if task.status != AgentTaskStatus.QUEUED:
            return task
        task.status = AgentTaskStatus.RUNNING
        task.save(update_fields=["status"])
    dashboard_data = dashboard(task.requested_by, task.tenant_id, task.profile_id)
    campaigns = [
        {
            "date": item["date"],
            "campaignId": item["campaign_id"],
            "campaignName": item["campaign_name"],
            "spend": item["spend"],
            "sales": item["sales"],
            "acos": item["acos"],
            "budgetSnapshot": item["budget_snapshot"],
            "stateSnapshot": item["state_snapshot"],
            "anomalies": item["anomalies"],
        }
        for item in dashboard_data["series"]
    ]
    payload = {
        "runId": str(task.pk),
        "tenantId": str(task.tenant_id),
        "profileId": str(task.profile_id),
        "campaigns": campaigns,
        "evidence": [{"source": "CampaignDailyMetric"}],
    }
    provider = MockLLMProvider()
    outputs = []
    try:
        for agent_type in (
            DataAnalysisAgent,
            AnomalyDiagnosisAgent,
            BudgetAnalysisAgent,
            StrategyAgent,
        ):
            output = agent_type(provider).run(payload)
            AgentRun.objects.create(
                task=task,
                agent_code=output["agentCode"],
                schema_version=output["schemaVersion"],
                status=AgentTaskStatus.SUCCEEDED,
                output=output,
            )
            outputs.append(output)
        recommendations = persist_recommendations(
            task=task, items=outputs[-1]["recommendations"]
        )
    except Exception as exc:
        task.status = AgentTaskStatus.FAILED
        task.error = str(exc)[:500]
    else:
        task.status = AgentTaskStatus.SUCCEEDED
        task.result = {
            "schemaVersion": "1.0",
            "runs": [output["agentCode"] for output in outputs],
            "recommendationIds": [str(item.pk) for item in recommendations],
        }
    task.completed_at = timezone.now()
    task.save(update_fields=["status", "result", "error", "completed_at"])
    return task
