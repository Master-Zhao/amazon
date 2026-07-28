import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.advertising.models import Campaign
from apps.agents.models import AgentCode, AgentRun, AgentRunStatus
from apps.agents.orchestrator import AnalysisOrchestrator
from apps.agents.selectors import authorized_analysis_input
from apps.audit.services import append_audit_log
from apps.permissions.models import ProfileAccessLevel
from apps.permissions.services import require_profile_scope
from apps.recommendations.models import (
    ActionType,
    LLMInvocation,
    Recommendation,
    RecommendationRevision,
)
from integrations.llm.providers import get_llm_provider


@dataclass(frozen=True, slots=True)
class SystemRequest:
    request_id: str


@transaction.atomic
def create_agent_run(*, request, tenant_id, profile_id) -> AgentRun:
    scope = require_profile_scope(
        user=request.user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="analysis.run",
        minimum_level=ProfileAccessLevel.OPERATE,
    )
    celery_task_id = uuid.uuid4().hex
    run = AgentRun.objects.create(
        tenant=scope.membership.tenant,
        profile=scope.profile,
        requested_by=request.user,
        celery_task_id=celery_task_id,
    )
    append_audit_log(
        request=request,
        tenant=scope.membership.tenant,
        actor=request.user,
        event="agent_run.queued",
        object_type="AgentRun",
        object_id=run.pk,
        task_id=str(run.pk),
        after_data={
            "profile_id": str(scope.profile.pk),
            "provider": settings.LLM_PROVIDER,
        },
    )
    from apps.agents.tasks import process_agent_run_task

    transaction.on_commit(
        lambda: process_agent_run_task.apply_async(
            args=[run.pk],
            task_id=celery_task_id,
        )
    )
    return run


def _validate_recommendation(
    *,
    run: AgentRun,
    payload: dict[str, object],
) -> tuple[Campaign, Decimal, Decimal]:
    if payload["actionType"] != ActionType.UPDATE_CAMPAIGN_BUDGET:
        raise ValueError("The demo milestone only publishes Campaign budget actions")
    if payload["objectType"] != "Campaign":
        raise ValueError("Recommendation objectType must be Campaign")
    campaign = (
        Campaign.objects.select_related("profile")
        .filter(pk=payload["objectId"], profile=run.profile)
        .first()
    )
    if campaign is None:
        raise ValueError("Recommendation Campaign is outside the authorized Profile")
    before_payload = payload["beforeValue"]
    after_payload = payload["afterValue"]
    if not isinstance(before_payload, dict) or not isinstance(after_payload, dict):
        raise ValueError("beforeValue and afterValue must be objects")
    if (
        before_payload.get("currency") != campaign.currency_code
        or after_payload.get("currency") != campaign.currency_code
    ):
        raise ValueError("Recommendation currency does not match Campaign currency")
    try:
        before = Decimal(str(before_payload["dailyBudget"]))
        after = Decimal(str(after_payload["dailyBudget"]))
    except (KeyError, InvalidOperation) as exc:
        raise ValueError("Campaign budget values must be decimals") from exc
    if campaign.daily_budget is None or before != campaign.daily_budget:
        raise ValueError("Recommendation beforeValue does not match current Campaign")
    if not settings.ACTION_MIN_DAILY_BUDGET <= after <= settings.ACTION_MAX_DAILY_BUDGET:
        raise ValueError("Recommended Campaign budget is outside configured bounds")
    if before == after:
        raise ValueError("Recommended Campaign budget must change")
    return campaign, before, after


def _mark_failed(*, run_id: int, error: Exception) -> AgentRun:
    with transaction.atomic():
        run = (
            AgentRun.objects.select_for_update()
            .select_related("tenant", "requested_by")
            .get(pk=run_id)
        )
        run.status = AgentRunStatus.FAILED
        run.error_code = "AGENT_RUN_FAILED"
        run.error_message = str(error)[:2000]
        run.finished_at = timezone.now()
        run.save(
            update_fields=[
                "status",
                "error_code",
                "error_message",
                "finished_at",
            ]
        )
        append_audit_log(
            request=SystemRequest(request_id=f"agent-run-{run.pk}"),
            tenant=run.tenant,
            actor=run.requested_by,
            event="agent_run.failed",
            object_type="AgentRun",
            object_id=run.pk,
            task_id=str(run.pk),
            after_data={"error_code": run.error_code},
        )
        return run


def process_agent_run(*, run_id: int) -> AgentRun:
    with transaction.atomic():
        run = (
            AgentRun.objects.select_for_update()
            .select_related(
                "tenant",
                "profile__store_marketplace__store__tenant",
                "requested_by",
            )
            .get(pk=run_id)
        )
        if run.status == AgentRunStatus.SUCCEEDED:
            return run
        if run.status == AgentRunStatus.RUNNING:
            return run
        run.status = AgentRunStatus.RUNNING
        run.started_at = timezone.now()
        run.save(update_fields=["status", "started_at"])

    try:
        context = authorized_analysis_input(profile=run.profile)
        provider = get_llm_provider()
        results = AnalysisOrchestrator(provider).run(
            run_id=str(run.pk),
            authorized_context=context,
        )
        final_result = results[-1]
        with transaction.atomic():
            locked = (
                AgentRun.objects.select_for_update()
                .select_related("tenant", "profile", "requested_by")
                .get(pk=run.pk)
            )
            locked.input_snapshot = context
            for result in results:
                LLMInvocation.objects.create(
                    agent_run=locked,
                    provider_code=provider.provider_code,
                    agent_code=str(result["agentCode"]),
                    request_payload=context,
                    response_payload=result,
                )
            created_recommendations = 0
            for payload in final_result["recommendations"]:
                campaign, _, _ = _validate_recommendation(
                    run=locked,
                    payload=payload,
                )
                recommendation = Recommendation.objects.create(
                    tenant=locked.tenant,
                    profile=locked.profile,
                    campaign=campaign,
                    agent_run=locked,
                    action_type=str(payload["actionType"]),
                )
                RecommendationRevision.objects.create(
                    recommendation=recommendation,
                    revision_number=1,
                    schema_version=str(final_result["schemaVersion"]),
                    action_type=str(payload["actionType"]),
                    object_type=str(payload["objectType"]),
                    object_id=str(payload["objectId"]),
                    before_value=payload["beforeValue"],
                    after_value=payload["afterValue"],
                    reason=str(payload["reason"]),
                    evidence=payload["evidence"],
                    risk_level=str(payload["riskLevel"]),
                )
                created_recommendations += 1
            locked.status = AgentRunStatus.SUCCEEDED
            locked.output_result = final_result
            locked.finished_at = timezone.now()
            locked.save(
                update_fields=[
                    "status",
                    "input_snapshot",
                    "output_result",
                    "finished_at",
                ]
            )
            append_audit_log(
                request=SystemRequest(request_id=f"agent-run-{locked.pk}"),
                tenant=locked.tenant,
                actor=locked.requested_by,
                event="agent_run.completed",
                object_type="AgentRun",
                object_id=locked.pk,
                task_id=str(locked.pk),
                after_data={
                    "provider": provider.provider_code,
                    "agent_count": len(results),
                    "recommendation_count": created_recommendations,
                },
            )
            return locked
    except Exception as exc:
        return _mark_failed(run_id=run.pk, error=exc)
