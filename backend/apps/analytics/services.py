from datetime import date
from decimal import Decimal

from django.db import transaction

from apps.analytics.calculations import calculate_metrics
from apps.analytics.models import (
    AnomalyRecord,
    AnomalyRuleVersion,
    CampaignDailyMetric,
    RiskLevel,
    RuleScope,
    SearchTermDailyMetric,
    TargetingDailyMetric,
)
from apps.reports.models import ReportType


def _raw(row):
    values = {
        "impressions": int(row.get("impressions") or 0),
        "clicks": int(row.get("clicks") or 0),
        "spend": Decimal(str(row.get("spend") or 0)),
        "orders": int(row.get("orders") or 0),
        "sales": Decimal(str(row.get("sales") or 0)),
    }
    return {**values, **calculate_metrics(**values)}


@transaction.atomic
def upsert_daily_metric(*, report_type, profile, batch, row, normalized_object):
    business_date = date.fromisoformat(str(row["date"]))
    values = {**_raw(row), "currency": profile.currency, "source_batch": batch}
    if report_type == ReportType.CAMPAIGN:
        campaign = normalized_object
        metric, _ = CampaignDailyMetric.objects.update_or_create(
            campaign=campaign,
            business_date=business_date,
            defaults={
                **values,
                "budget_snapshot": campaign.daily_budget,
                "state_snapshot": campaign.state,
            },
        )
        evaluate_campaign_metric(metric)
        return metric
    if report_type == ReportType.TARGETING:
        target = normalized_object
        is_keyword = target.__class__.__name__ == "Keyword"
        metric, _ = TargetingDailyMetric.objects.update_or_create(
            keyword=target if is_keyword else None,
            product_target=None if is_keyword else target,
            business_date=business_date,
            defaults={
                **values,
                "profile": profile,
                "targeting_type": "KEYWORD" if is_keyword else "PRODUCT",
                "bid_snapshot": target.bid,
                "state_snapshot": target.state,
            },
        )
        return metric
    return SearchTermDailyMetric.objects.update_or_create(
        search_term=normalized_object,
        business_date=business_date,
        defaults=values,
    )[0]


def target_acos_for(campaign):
    value = (
        campaign.target_acos
        or campaign.profile.target_acos
        or campaign.profile.store_marketplace.store.tenant.target_acos
    )
    return Decimal(str(value)) if value is not None else None


def _default_rule():
    rule, _ = AnomalyRuleVersion.objects.get_or_create(
        code="HIGH_ACOS",
        scope=RuleScope.SYSTEM,
        tenant=None,
        profile=None,
        campaign=None,
        version=1,
        defaults={"thresholds": {"minimumClicks": 5, "multiplier": "1.20"}},
    )
    return rule


def evaluate_campaign_metric(metric):
    rule = _default_rule()
    target = target_acos_for(metric.campaign)
    if metric.clicks < int(rule.thresholds["minimumClicks"]) or metric.acos is None or target is None:
        status = "INSUFFICIENT_DATA"
        risk = RiskLevel.LOW
    elif metric.acos > Decimal(str(target)) * Decimal(rule.thresholds["multiplier"]):
        status = "ANOMALOUS"
        risk = RiskLevel.HIGH
    else:
        status = "NORMAL"
        risk = RiskLevel.LOW
    AnomalyRecord.objects.update_or_create(
        metric=metric,
        rule_version=rule,
        defaults={
            "status": status,
            "risk_level": risk,
            "evidence": {
                "acos": str(metric.acos) if metric.acos is not None else None,
                "targetAcos": str(target) if target is not None else None,
            },
        },
    )
