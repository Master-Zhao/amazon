from django.db.models import Sum
from rest_framework.exceptions import NotFound

from apps.analytics.calculations import calculate_metrics
from apps.analytics.models import (
    CampaignDailyMetric,
    SearchTermDailyMetric,
    TargetingDailyMetric,
)
from apps.permissions.services import authorize
from apps.stores.models import AdvertisingProfile


def _profile(user, tenant_id, profile_id):
    try:
        profile = AdvertisingProfile.objects.select_related(
            "store_marketplace__store"
        ).get(pk=profile_id)
    except (AdvertisingProfile.DoesNotExist, ValueError) as exc:
        raise NotFound("广告 Profile 不存在") from exc
    authorize(
        user=user,
        tenant_id=tenant_id,
        permission_code="analytics.view",
        profile=profile,
    )
    return profile


def _totals(queryset):
    totals = queryset.aggregate(
        impressions=Sum("impressions"),
        clicks=Sum("clicks"),
        spend=Sum("spend"),
        orders=Sum("orders"),
        sales=Sum("sales"),
    )
    raw = {key: value or 0 for key, value in totals.items()}
    return {**raw, **calculate_metrics(**raw)}


def dashboard(user, tenant_id, profile_id):
    profile = _profile(user, tenant_id, profile_id)
    metrics = CampaignDailyMetric.objects.filter(campaign__profile=profile)
    totals = _totals(metrics)
    return {
        "currency": profile.currency,
        "totals": totals,
        "series": [
            {
                "date": str(metric.business_date),
                "campaign_id": str(metric.campaign_id),
                "campaign_name": metric.campaign.name,
                "spend": str(metric.spend),
                "sales": str(metric.sales),
                "acos": str(metric.acos) if metric.acos is not None else None,
                "budget_snapshot": (
                    str(metric.budget_snapshot)
                    if metric.budget_snapshot is not None
                    else None
                ),
                "state_snapshot": metric.state_snapshot,
                "anomalies": [
                    {
                        "status": item.status,
                        "risk_level": item.risk_level,
                        "evidence": item.evidence,
                    }
                    for item in metric.anomalies.all()
                ],
            }
            for metric in metrics.select_related("campaign").prefetch_related(
                "anomalies"
            ).order_by("business_date", "campaign__name")[:500]
        ],
    }


def targeting_metrics(user, tenant_id, profile_id):
    profile = _profile(user, tenant_id, profile_id)
    return {
        "currency": profile.currency,
        "items": list(
            TargetingDailyMetric.objects.filter(profile=profile)
            .values(
                "business_date",
                "targeting_type",
                "impressions",
                "clicks",
                "spend",
                "orders",
                "sales",
                "acos",
                "bid_snapshot",
                "state_snapshot",
            )[:500]
        ),
    }


def search_term_metrics(user, tenant_id, profile_id):
    profile = _profile(user, tenant_id, profile_id)
    return {
        "currency": profile.currency,
        "items": list(
            SearchTermDailyMetric.objects.filter(search_term__profile=profile)
            .values(
                "business_date",
                "search_term__query_text",
                "impressions",
                "clicks",
                "spend",
                "orders",
                "sales",
                "acos",
            )[:500]
        ),
    }

