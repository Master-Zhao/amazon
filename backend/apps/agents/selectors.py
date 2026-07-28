from apps.analytics.models import CampaignDailyMetric
from apps.permissions.models import ProfileAccessLevel
from apps.permissions.services import require_profile_scope


def authorized_analysis_input(*, profile) -> dict[str, object]:
    metrics = (
        CampaignDailyMetric.objects.filter(profile=profile)
        .select_related("campaign", "source_batch")
        .prefetch_related("anomaly_records__rule_version")
        .order_by("campaign_id", "-report_date", "-id")
    )
    latest_by_campaign = {}
    for metric in metrics:
        latest_by_campaign.setdefault(metric.campaign_id, metric)

    campaigns: list[dict[str, object]] = []
    for metric in latest_by_campaign.values():
        anomalies = [
            {
                "ruleCode": record.rule_version.code,
                "ruleVersion": record.rule_version.version,
                "status": record.status,
                "riskLevel": record.risk_level,
                "observedValue": (
                    str(record.observed_value)
                    if record.observed_value is not None
                    else None
                ),
                "thresholdValue": (
                    str(record.threshold_value)
                    if record.threshold_value is not None
                    else None
                ),
                "reasonCode": record.reason_code,
            }
            for record in metric.anomaly_records.all()
            if record.source_batch_id == metric.source_batch_id
        ]
        campaigns.append(
            {
                "campaignId": str(metric.campaign_id),
                "externalCampaignId": metric.campaign.external_campaign_id,
                "metricId": str(metric.pk),
                "reportDate": metric.report_date.isoformat(),
                "dailyBudget": (
                    str(metric.campaign.daily_budget)
                    if metric.campaign.daily_budget is not None
                    else None
                ),
                "currency": metric.currency_code,
                "impressions": metric.impressions,
                "clicks": metric.clicks,
                "spend": str(metric.spend),
                "orders": metric.orders,
                "sales": str(metric.sales),
                "sourceBatchId": str(metric.source_batch_id),
                "anomalies": anomalies,
            }
        )
    return {
        "schemaVersion": "analysis-input-v1",
        "profileId": str(profile.pk),
        "externalProfileId": profile.external_profile_id,
        "currency": profile.currency_code,
        "campaigns": campaigns,
    }


def agent_runs_for_profile(*, user, tenant_id, profile_id):
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="recommendations.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    return scope, scope.profile.agent_runs.select_related("requested_by").order_by(
        "-created_at"
    )
