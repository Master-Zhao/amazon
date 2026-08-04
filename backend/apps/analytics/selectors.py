from datetime import date
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from rest_framework.exceptions import NotFound
from rest_framework.serializers import ValidationError

from apps.advertising.models import Campaign
from apps.analytics.models import (
    AnomalyRuleVersion,
    AnomalyRecord,
    AnomalyStatus,
    CampaignDailyMetric,
    SearchTermDailyMetric,
    TargetingDailyMetric,
)
from apps.analytics.services import metric_formulas, resolve_target_acos
from apps.permissions.models import ProfileAccessLevel
from apps.permissions.services import require_profile_scope
from integrations.advertising_data.remote_databases import (
    RemoteAdvertisingDataReader,
    remote_scope_for_profile,
)


def _date(value: str | None, field: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError({field: ["Use YYYY-MM-DD."]}) from exc


def _decimal_string(value: Decimal | None) -> str | None:
    return format(value, "f") if value is not None else None


def _canonical_decimal_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _formula_payload(item: dict[str, Decimal | str | None]) -> dict[str, str | None]:
    value = item["value"]
    return {
        "value": _decimal_string(value if isinstance(value, Decimal) else None),
        "reason": item["reason"] if isinstance(item["reason"], str) else None,
    }


def dashboard_rows(
    *,
    user,
    tenant_id,
    profile_id,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, object]]:
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="analytics.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    start = _date(start_date, "start_date")
    end = _date(end_date, "end_date")
    if start and end and start > end:
        raise ValidationError({"end_date": ["Must be on or after start_date."]})
    metrics = CampaignDailyMetric.objects.filter(profile=scope.profile)
    anomaly_records = AnomalyRecord.objects.filter(
        metric__profile=scope.profile,
        status=AnomalyStatus.ANOMALY,
        source_batch=F("metric__source_batch"),
    )
    if start:
        metrics = metrics.filter(report_date__gte=start)
        anomaly_records = anomaly_records.filter(metric__report_date__gte=start)
    if end:
        metrics = metrics.filter(report_date__lte=end)
        anomaly_records = anomaly_records.filter(metric__report_date__lte=end)
    anomaly_counts = {
        (row["metric__currency_code"], row["metric__profile_id"]): row["count"]
        for row in anomaly_records.values(
            "metric__currency_code",
            "metric__profile_id",
        ).annotate(count=Count("id"))
    }
    aggregates = metrics.values(
        "profile_id",
        "profile__store_marketplace__marketplace__code",
        "profile__store_marketplace__marketplace__name",
        "currency_code",
    ).annotate(
        campaign_count=Count("campaign_id", distinct=True),
        impressions=Sum("impressions"),
        clicks=Sum("clicks"),
        spend=Sum("spend"),
        orders=Sum("orders"),
        sales=Sum("sales"),
    )
    result: list[dict[str, object]] = []
    for row in aggregates.order_by(
        "profile__store_marketplace__marketplace__code",
        "currency_code",
    ):
        formulas = metric_formulas(
            impressions=row["impressions"],
            clicks=row["clicks"],
            spend=row["spend"],
            orders=row["orders"],
            sales=row["sales"],
        )
        result.append(
            {
                "marketplace_code": row[
                    "profile__store_marketplace__marketplace__code"
                ],
                "marketplace_name": row[
                    "profile__store_marketplace__marketplace__name"
                ],
                "currency_code": row["currency_code"],
                "campaign_count": row["campaign_count"],
                "impressions": row["impressions"],
                "clicks": row["clicks"],
                "spend": _canonical_decimal_string(row["spend"]),
                "orders": row["orders"],
                "sales": _canonical_decimal_string(row["sales"]),
                "ctr": _formula_payload(formulas["ctr"]),
                "cpc": _formula_payload(formulas["cpc"]),
                "cvr": _formula_payload(formulas["cvr"]),
                "acos": _formula_payload(formulas["acos"]),
                "roas": _formula_payload(formulas["roas"]),
                "anomaly_count": anomaly_counts.get(
                    (row["currency_code"], row["profile_id"]),
                    0,
                ),
                "authoritative_grain": "CAMPAIGN_DAILY_METRIC",
            }
        )
    return result


def campaign_metric_rows(
    *,
    user,
    tenant_id,
    profile_id,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, object]]:
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="analytics.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    start = _date(start_date, "start_date")
    end = _date(end_date, "end_date")
    if start and end and start > end:
        raise ValidationError(
            {"end_date": ["Must be on or after start_date."]}
        )
    metrics = CampaignDailyMetric.objects.filter(
        profile=scope.profile,
    ).select_related(
        "campaign",
        "campaign__profile__store_marketplace__store__tenant",
        "source_batch",
    ).prefetch_related(
        "anomaly_records__rule_version",
    )
    if start:
        metrics = metrics.filter(report_date__gte=start)
    if end:
        metrics = metrics.filter(report_date__lte=end)

    rows: list[dict[str, object]] = []
    for metric in metrics.order_by("-report_date", "campaign__name", "campaign_id"):
        formulas = metric_formulas(
            impressions=metric.impressions,
            clicks=metric.clicks,
            spend=metric.spend,
            orders=metric.orders,
            sales=metric.sales,
        )
        anomalies = [
            {
                "id": str(record.pk),
                "rule_code": record.rule_version.code,
                "rule_version": record.rule_version.version,
                "status": record.status,
                "risk_level": record.risk_level,
                "observed_value": _decimal_string(record.observed_value),
                "threshold_value": _decimal_string(record.threshold_value),
                "reason_code": record.reason_code,
                "explanation": record.explanation,
            }
            for record in metric.anomaly_records.all()
            if record.source_batch_id == metric.source_batch_id
        ]
        rows.append(
            {
                "id": str(metric.pk),
                "campaign_id": str(metric.campaign_id),
                "external_campaign_id": metric.campaign.external_campaign_id,
                "campaign_name": metric.campaign.name,
                "report_date": metric.report_date,
                "currency_code": metric.currency_code,
                "impressions": metric.impressions,
                "clicks": metric.clicks,
                "spend": _decimal_string(metric.spend),
                "orders": metric.orders,
                "sales": _decimal_string(metric.sales),
                "calculation_reasons": metric.calculation_reasons,
                "daily_budget_snapshot": _decimal_string(
                    metric.daily_budget_snapshot
                ),
                "snapshot_hour_local": metric.snapshot_hour_local,
                "state_snapshot": metric.state_snapshot,
                "target_acos": _decimal_string(
                    resolve_target_acos(metric.campaign)
                ),
                "ctr": _formula_payload(formulas["ctr"]),
                "cpc": _formula_payload(formulas["cpc"]),
                "cvr": _formula_payload(formulas["cvr"]),
                "acos": _formula_payload(formulas["acos"]),
                "roas": _formula_payload(formulas["roas"]),
                "source_batch_id": str(metric.source_batch_id),
                "anomalies": anomalies,
            }
        )
    return rows


def campaign_detail(
    *,
    user,
    tenant_id,
    profile_id,
    campaign_id,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, object]:
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="analytics.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    campaign = Campaign.objects.filter(
        pk=campaign_id,
        profile=scope.profile,
    ).first()
    if campaign is None:
        raise NotFound("Campaign does not exist in the current Profile scope.")
    metrics = campaign_metric_rows(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        start_date=start_date,
        end_date=end_date,
    )
    return {
        "campaign_id": str(campaign.pk),
        "external_campaign_id": campaign.external_campaign_id,
        "campaign_name": campaign.name,
        "state": campaign.state,
        "target_acos": _decimal_string(resolve_target_acos(campaign)),
        "metrics": [
            row for row in metrics if row["campaign_id"] == str(campaign.pk)
        ],
    }


def analytics_configuration(
    *,
    user,
    tenant_id,
    profile_id,
) -> dict[str, object]:
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="analytics.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    campaigns = list(
        Campaign.objects.filter(profile=scope.profile).order_by("name", "id")
    )
    scope_keys = [
        "SYSTEM",
        f"TENANT:{scope.membership.tenant_id}",
        f"PROFILE:{scope.profile.pk}",
        *(f"CAMPAIGN:{campaign.pk}" for campaign in campaigns),
    ]
    latest_rules: dict[tuple[str, str], AnomalyRuleVersion] = {}
    for rule in AnomalyRuleVersion.objects.filter(
        is_active=True,
    ).filter(
        Q(scope_key__in=scope_keys)
    ).order_by("scope_key", "code", "-version", "-created_at"):
        latest_rules.setdefault((rule.scope_key, rule.code), rule)
    return {
        "tenant_target_acos": _decimal_string(scope.membership.tenant.target_acos),
        "profile_target_acos": _decimal_string(scope.profile.target_acos),
        "campaigns": [
            {
                "campaign_id": str(campaign.pk),
                "campaign_name": campaign.name,
                "target_acos": _decimal_string(campaign.target_acos),
                "effective_target_acos": _decimal_string(
                    resolve_target_acos(campaign)
                ),
            }
            for campaign in campaigns
        ],
        "rules": [
            {
                "id": str(rule.pk),
                "code": rule.code,
                "version": rule.version,
                "scope_key": rule.scope_key,
                "configuration": rule.configuration,
                "created_at": rule.created_at,
            }
            for rule in latest_rules.values()
        ],
    }


def targeting_metric_rows(
    *,
    user,
    tenant_id,
    profile_id,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, object]]:
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="analytics.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    start = _date(start_date, "start_date")
    end = _date(end_date, "end_date")
    if start and end and start > end:
        raise ValidationError({"end_date": ["Must be on or after start_date."]})
    metrics = TargetingDailyMetric.objects.filter(
        profile=scope.profile,
    ).select_related(
        "campaign",
        "ad_group",
        "keyword",
        "product_target",
        "source_batch",
    )
    if start:
        metrics = metrics.filter(report_date__gte=start)
    if end:
        metrics = metrics.filter(report_date__lte=end)
    rows: list[dict[str, object]] = []
    for metric in metrics.order_by(
        "-report_date",
        "campaign__name",
        "ad_group__name",
        "target_key",
    ):
        formulas = metric_formulas(
            impressions=metric.impressions,
            clicks=metric.clicks,
            spend=metric.spend,
            orders=metric.orders,
            sales=metric.sales,
        )
        entity = metric.keyword or metric.product_target
        rows.append(
            {
                "id": str(metric.pk),
                "campaign_id": str(metric.campaign_id),
                "campaign_name": metric.campaign.name,
                "ad_group_id": str(metric.ad_group_id),
                "ad_group_name": metric.ad_group.name,
                "target_type": metric.target_type,
                "target_id": (
                    entity.external_keyword_id
                    if metric.keyword_id
                    else entity.external_target_id
                ),
                "target_text": (
                    entity.keyword_text
                    if metric.keyword_id
                    else entity.expression
                ),
                "match_type": (
                    metric.keyword.match_type if metric.keyword_id else None
                ),
                "report_date": metric.report_date,
                "currency_code": metric.currency_code,
                "impressions": metric.impressions,
                "clicks": metric.clicks,
                "spend": _decimal_string(metric.spend),
                "orders": metric.orders,
                "sales": _decimal_string(metric.sales),
                "calculation_reasons": metric.calculation_reasons,
                "bid_snapshot": _decimal_string(metric.bid_snapshot),
                "state_snapshot": metric.state_snapshot,
                "ctr": _formula_payload(formulas["ctr"]),
                "cpc": _formula_payload(formulas["cpc"]),
                "cvr": _formula_payload(formulas["cvr"]),
                "acos": _formula_payload(formulas["acos"]),
                "roas": _formula_payload(formulas["roas"]),
                "source_batch_id": str(metric.source_batch_id),
            }
        )
    return rows


def search_term_metric_rows(
    *,
    user,
    tenant_id,
    profile_id,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, object]]:
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="analytics.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    start = _date(start_date, "start_date")
    end = _date(end_date, "end_date")
    if start and end and start > end:
        raise ValidationError({"end_date": ["Must be on or after start_date."]})
    metrics = SearchTermDailyMetric.objects.filter(
        profile=scope.profile,
    ).select_related(
        "campaign",
        "ad_group",
        "search_term",
        "source_batch",
    )
    if start:
        metrics = metrics.filter(report_date__gte=start)
    if end:
        metrics = metrics.filter(report_date__lte=end)
    rows: list[dict[str, object]] = []
    for metric in metrics.order_by(
        "-report_date",
        "campaign__name",
        "ad_group__name",
        "search_term__display_text",
    ):
        formulas = metric_formulas(
            impressions=metric.impressions,
            clicks=metric.clicks,
            spend=metric.spend,
            orders=metric.orders,
            sales=metric.sales,
        )
        rows.append(
            {
                "id": str(metric.pk),
                "campaign_id": str(metric.campaign_id),
                "campaign_name": metric.campaign.name,
                "ad_group_id": str(metric.ad_group_id),
                "ad_group_name": metric.ad_group.name,
                "search_term_id": str(metric.search_term_id),
                "search_term": metric.search_term.display_text,
                "targeting_expression": metric.targeting_expression_snapshot,
                "report_date": metric.report_date,
                "currency_code": metric.currency_code,
                "impressions": metric.impressions,
                "clicks": metric.clicks,
                "spend": _decimal_string(metric.spend),
                "orders": metric.orders,
                "sales": _decimal_string(metric.sales),
                "calculation_reasons": metric.calculation_reasons,
                "ctr": _formula_payload(formulas["ctr"]),
                "cpc": _formula_payload(formulas["cpc"]),
                "cvr": _formula_payload(formulas["cvr"]),
                "acos": _formula_payload(formulas["acos"]),
                "roas": _formula_payload(formulas["roas"]),
                "source_batch_id": str(metric.source_batch_id),
            }
        )
    return rows


def remote_campaign_metric_rows(
    *,
    user,
    tenant_id,
    profile_id,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, object]]:
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="analytics.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    start = _date(start_date, "start_date")
    end = _date(end_date, "end_date")
    if start and end and start > end:
        raise ValidationError({"end_date": ["Must be on or after start_date."]})

    remote_scope = remote_scope_for_profile(scope.profile)
    metrics = RemoteAdvertisingDataReader().campaign_metrics(
        merchant_id=remote_scope.merchant_id,
        merchant_code=remote_scope.merchant_code,
        start_date=start,
        end_date=end,
    )
    rows: list[dict[str, object]] = []
    for metric in metrics:
        formulas = metric_formulas(
            impressions=metric.impressions,
            clicks=metric.clicks,
            spend=metric.spend,
            orders=metric.orders,
            sales=metric.sales,
        )
        rows.append(
            {
                "id": (
                    f"remote:{metric.report_date.isoformat()}:"
                    f"{metric.external_campaign_id}"
                ),
                "external_campaign_id": metric.external_campaign_id,
                "campaign_name": metric.campaign_name,
                "report_date": metric.report_date,
                "currency_code": scope.profile.currency_code,
                "impressions": metric.impressions,
                "clicks": metric.clicks,
                "spend": _decimal_string(metric.spend),
                "orders": metric.orders,
                "sales": _decimal_string(metric.sales),
                "daily_budget": _decimal_string(metric.daily_budget),
                "state": metric.state,
                "ctr": _formula_payload(formulas["ctr"]),
                "cpc": _formula_payload(formulas["cpc"]),
                "cvr": _formula_payload(formulas["cvr"]),
                "acos": _formula_payload(formulas["acos"]),
                "roas": _formula_payload(formulas["roas"]),
                "scm_matched": metric.scm_matched,
                "source_system": "REMOTE_MYSQL",
            }
        )
    return rows
