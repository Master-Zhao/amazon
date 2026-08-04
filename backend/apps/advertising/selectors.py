import hashlib
from decimal import Decimal

from apps.advertising.models import Campaign, Keyword, ProductTarget, SearchTerm
from apps.analytics.models import AnomalyRuleCode, AnomalyRuleVersion
from apps.analytics.services import SYSTEM_RULES, metric_formulas
from apps.permissions.models import ProfileAccessLevel
from apps.permissions.services import require_profile_scope
from integrations.advertising_data.remote_databases import (
    RemoteAdvertisingDataReader,
    remote_scope_for_profile,
)


def _decimal_string(value: Decimal | None) -> str | None:
    return format(value, "f") if value is not None else None


def _money(value: Decimal | None, currency_code: str) -> dict[str, str] | None:
    if value is None:
        return None
    return {"amount": _decimal_string(value), "currency_code": currency_code}


def _ratio(formula: dict[str, Decimal | str | None]) -> str | None:
    value = formula["value"]
    return _decimal_string(value if isinstance(value, Decimal) else None)


def _normalized_status(value: str) -> str:
    return {
        "enabled": "DELIVERING",
        "paused": "PAUSED",
        "archived": "ARCHIVED",
        "ended": "ENDED",
        "applying": "REVIEWING",
        "refuse": "REJECTED",
        "nothing": "UNKNOWN",
    }.get(value.strip().lower(), "UNKNOWN")


def _normalized_targeting_type(value: str) -> str:
    normalized = value.strip().upper()
    if normalized in {"AUTO", "AUTOMATIC"}:
        return "AUTO"
    if normalized in {"MANUAL", "MANUAL_TARGETING"}:
        return "MANUAL"
    return "UNKNOWN"


def _campaign_key(merchant_id: int, merchant_code: str, value: str) -> str:
    digest = hashlib.sha256(
        f"{merchant_id}:{merchant_code}:{value}".encode("utf-8")
    ).hexdigest()
    return f"cmp_{digest[:24]}"


def _metric_payload(*, metric, currency_code: str) -> dict[str, object]:
    formulas = metric_formulas(
        impressions=metric.impressions,
        clicks=metric.clicks,
        spend=metric.spend,
        orders=metric.orders,
        sales=metric.sales,
    )
    return {
        "impressions": metric.impressions,
        "top_of_search_share": None,
        "spend": _money(metric.spend, currency_code),
        "sales": _money(metric.sales, currency_code),
        "clicks": metric.clicks,
        "ctr": _ratio(formulas["ctr"]),
        "total_cost": _money(metric.spend, currency_code),
        "orders": metric.orders,
        "cpc": _money(
            formulas["cpc"]["value"]
            if isinstance(formulas["cpc"]["value"], Decimal)
            else None,
            currency_code,
        ),
        "acos": _ratio(formulas["acos"]),
        "cvr": _ratio(formulas["cvr"]),
    }


def _dashboard_rule_configuration(*, tenant_id, profile_id) -> dict[str, dict]:
    configurations = {code: dict(value) for code, value in SYSTEM_RULES.items()}
    scope_keys = (f"PROFILE:{profile_id}", f"TENANT:{tenant_id}")
    for code in configurations:
        for scope_key in scope_keys:
            rule = (
                AnomalyRuleVersion.objects.filter(
                    code=code,
                    scope_key=scope_key,
                    is_active=True,
                )
                .order_by("-version", "-created_at")
                .first()
            )
            if rule is not None:
                configurations[code] = dict(rule.configuration)
                break
    return configurations


def _risk_level(*, metric, rules: dict[str, dict], target_acos: Decimal | None) -> str:
    formulas = metric_formulas(
        impressions=metric.impressions,
        clicks=metric.clicks,
        spend=metric.spend,
        orders=metric.orders,
        sales=metric.sales,
    )
    high_count = 0
    medium_count = 0
    low_count = 0

    high_acos = rules[AnomalyRuleCode.HIGH_ACOS]
    acos = formulas["acos"]["value"]
    if (
        target_acos is not None
        and isinstance(acos, Decimal)
        and metric.clicks >= int(high_acos["minimum_clicks"])
        and metric.sales >= Decimal(str(high_acos["minimum_sales"]))
        and acos > target_acos
    ):
        if acos / target_acos >= Decimal("1.5"):
            high_count += 1
        else:
            medium_count += 1

    spend_rule = rules[AnomalyRuleCode.HIGH_SPEND_NO_ORDERS]
    if metric.spend >= Decimal(str(spend_rule["minimum_spend"])) and metric.orders == 0:
        high_count += 1

    conversion_rule = rules[AnomalyRuleCode.HIGH_CLICKS_LOW_CONVERSION]
    cvr = formulas["cvr"]["value"]
    if (
        metric.clicks >= int(conversion_rule["minimum_clicks"])
        and isinstance(cvr, Decimal)
        and cvr <= Decimal(str(conversion_rule["maximum_cvr"]))
    ):
        medium_count += 1

    if metric.impressions < int(
        rules[AnomalyRuleCode.LOW_IMPRESSIONS]["minimum_impressions"]
    ):
        low_count += 1
    if metric.clicks < int(rules[AnomalyRuleCode.LOW_CLICKS]["minimum_clicks"]):
        low_count += 1

    if high_count >= 2:
        return "VERY_HIGH"
    if high_count:
        return "HIGH"
    if medium_count:
        return "MEDIUM"
    if low_count:
        return "LOW"
    return "VERY_LOW"


def _dashboard_payload(*, result, scope, currency_code: str) -> dict[str, object]:
    rules = _dashboard_rule_configuration(
        tenant_id=scope.membership.tenant_id,
        profile_id=scope.profile.pk,
    )
    target_acos = scope.profile.target_acos or scope.membership.tenant.target_acos
    counts = {level: 0 for level in ("VERY_HIGH", "HIGH", "MEDIUM", "LOW", "VERY_LOW")}
    for metric in result.risk_metrics:
        counts[_risk_level(metric=metric, rules=rules, target_acos=target_acos)] += 1
    return {
        "trend": [
            {
                "date": item.report_date,
                "metrics": _metric_payload(metric=item, currency_code=currency_code),
            }
            for item in result.trend
        ],
        "risk_levels": [
            {"level": level, "count": counts[level]}
            for level in ("VERY_HIGH", "HIGH", "MEDIUM", "LOW", "VERY_LOW")
        ],
        "evaluated_campaigns": len(result.risk_metrics),
        "target_acos": _decimal_string(target_acos),
        "unavailable_rule_codes": [AnomalyRuleCode.BUDGET_EARLY_EXHAUSTION],
        "risk_semantics": "SYSTEM_RULES_AGGREGATED",
    }


def campaign_overview_page(
    *, user, tenant_id, profile_id, query: dict[str, object]
) -> dict[str, object]:
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="advertising.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    remote_scope = remote_scope_for_profile(scope.profile)
    result = RemoteAdvertisingDataReader().campaign_overview(
        merchant_id=remote_scope.merchant_id,
        merchant_code=remote_scope.merchant_code,
        start_date=query.get("start_date"),
        end_date=query.get("end_date"),
        enabled=query.get("enabled"),
        statuses=query.get("statuses", ()),
        targeting_type=query.get("targeting_type"),
        search=query.get("search", ""),
        ordering=query.get("ordering", "-spend"),
        page=query.get("page", 1),
        page_size=query.get("page_size", 15),
        include_summary=query.get("include_summary", True),
    )
    currency_code = scope.profile.currency_code
    items = []
    for metric in result.items:
        partial_fields = ["topOfSearchShare", "ordersAttributionWindow"]
        if metric.start_date is None:
            partial_fields.append("startDate")
        if not metric.scm_matched:
            partial_fields.extend(
                [
                    "referenceCode",
                    "targetingType",
                    "biddingStrategy",
                    "endDate",
                ]
            )
        items.append(
            {
                "campaign_key": _campaign_key(
                    remote_scope.merchant_id,
                    remote_scope.merchant_code,
                    metric.campaign_key,
                ),
                "name": metric.campaign_name,
                "reference_code": metric.reference_code,
                "enabled": metric.state.strip().lower() == "enabled",
                "targeting_type": _normalized_targeting_type(metric.targeting_type),
                "status": _normalized_status(metric.state),
                "bidding_strategy": metric.bidding_strategy.strip().upper(),
                "start_date": metric.start_date,
                "end_date": metric.end_date,
                "daily_budget": _money(metric.daily_budget, currency_code),
                "metrics": _metric_payload(
                    metric=metric,
                    currency_code=currency_code,
                ),
                "metadata_matched": metric.scm_matched,
                "partial_fields": sorted(set(partial_fields)),
            }
        )

    summary = None
    if result.summary is not None:
        summary = _metric_payload(
            metric=result.summary,
            currency_code=currency_code,
        )
    total_pages = (
        (result.total + result.page_size - 1) // result.page_size
        if result.total
        else 0
    )
    return {
        "items": items,
        "summary": summary,
        "dashboard": _dashboard_payload(
            result=result,
            scope=scope,
            currency_code=currency_code,
        ),
        "pagination": {
            "page": result.page,
            "page_size": result.page_size,
            "total": result.total,
            "total_pages": total_pages,
        },
        "meta": {
            "source": "REMOTE_MYSQL",
            "currency_code": currency_code,
            "timezone": scope.profile.timezone,
            "start_date": result.start_date,
            "end_date": result.end_date,
            "data_through_date": result.data_through_date,
            "total_cost_semantics": "SPEND_ALIAS",
            "attribution_semantics": "REMOTE_FIELDS_UNVERIFIED",
            "status_filter_semantics": "ANALYSIS_FILTER_SCM_DISPLAY",
        },
    }


def campaign_rows(*, user, tenant_id, profile_id) -> list[dict[str, object]]:
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="advertising.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    return [
        {
            "id": str(item.pk),
            "external_campaign_id": item.external_campaign_id,
            "name": item.name,
            "ad_product_type": item.ad_product_type,
            "state": item.state,
            "daily_budget": (
                str(item.daily_budget) if item.daily_budget is not None else None
            ),
            "currency_code": item.currency_code,
            "source_batch_id": (
                str(item.source_batch_id) if item.source_batch_id else None
            ),
        }
        for item in Campaign.objects.filter(profile=scope.profile).order_by(
            "name",
            "external_campaign_id",
        )
    ]


def targeting_rows(*, user, tenant_id, profile_id) -> list[dict[str, object]]:
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="advertising.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    keywords = [
        {
            "id": str(item.pk),
            "target_type": "KEYWORD",
            "external_target_id": item.external_keyword_id,
            "target_text": item.keyword_text,
            "match_type": item.match_type,
            "state": item.state,
            "bid": str(item.bid) if item.bid is not None else None,
            "campaign_id": str(item.ad_group.campaign_id),
            "campaign_name": item.ad_group.campaign.name,
            "ad_group_id": str(item.ad_group_id),
            "ad_group_name": item.ad_group.name,
            "source_batch_id": (
                str(item.source_batch_id) if item.source_batch_id else None
            ),
        }
        for item in Keyword.objects.select_related(
            "ad_group__campaign"
        ).filter(
            ad_group__campaign__profile=scope.profile,
        )
    ]
    targets = [
        {
            "id": str(item.pk),
            "target_type": "PRODUCT_TARGET",
            "external_target_id": item.external_target_id,
            "target_text": item.expression,
            "match_type": None,
            "state": item.state,
            "bid": str(item.bid) if item.bid is not None else None,
            "campaign_id": str(item.ad_group.campaign_id),
            "campaign_name": item.ad_group.campaign.name,
            "ad_group_id": str(item.ad_group_id),
            "ad_group_name": item.ad_group.name,
            "source_batch_id": (
                str(item.source_batch_id) if item.source_batch_id else None
            ),
        }
        for item in ProductTarget.objects.select_related(
            "ad_group__campaign"
        ).filter(
            ad_group__campaign__profile=scope.profile,
        )
    ]
    return sorted(
        [*keywords, *targets],
        key=lambda item: (
            item["campaign_name"],
            item["ad_group_name"],
            item["target_type"],
            item["target_text"],
        ),
    )


def search_term_rows(*, user, tenant_id, profile_id) -> list[dict[str, object]]:
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="advertising.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    return [
        {
            "id": str(item.pk),
            "display_text": item.display_text,
            "normalized_text": item.normalized_text,
            "text_hash": item.text_hash,
        }
        for item in SearchTerm.objects.filter(profile=scope.profile).order_by(
            "normalized_text"
        )
    ]
