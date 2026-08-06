from decimal import Decimal

from apps.audit.services import append_audit_log
from django.core import signing
from rest_framework.exceptions import NotFound

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
    if normalized in {"AUTO", "AUTOMATIC"} or "AUTO" in normalized:
        return "AUTO"
    if normalized in {"MANUAL", "MANUAL_TARGETING"} or "MANUAL" in normalized:
        return "MANUAL"
    return "UNKNOWN"


def _campaign_key(merchant_id: int, merchant_code: str, value: str) -> str:
    encoded = signing.dumps(
        str(value),
        salt=f"campaign-key:{merchant_id}:{merchant_code}",
        compress=True,
    )
    return f"cmp_{encoded}"


def _raw_campaign_key(merchant_id: int, merchant_code: str, value: str) -> str:
    if not value.startswith("cmp_"):
        raise NotFound("广告活动不存在")
    try:
        decoded = signing.loads(
            value.removeprefix("cmp_"),
            salt=f"campaign-key:{merchant_id}:{merchant_code}",
        )
    except signing.BadSignature as exc:
        raise NotFound("广告活动不存在") from exc
    if not isinstance(decoded, str) or not decoded:
        raise NotFound("广告活动不存在")
    return decoded


def _metric_payload(*, metric, currency_code: str) -> dict[str, object]:
    if not getattr(metric, "has_metrics", True):
        return {
            "impressions": None,
            "top_of_search_share": None,
            "spend": None,
            "sales": None,
            "clicks": None,
            "ctr": None,
            "total_cost": None,
            "orders": None,
            "cpc": None,
            "acos": None,
            "cvr": None,
        }
    formulas = metric_formulas(
        impressions=metric.impressions,
        clicks=metric.clicks,
        spend=metric.spend,
        orders=metric.orders,
        sales=metric.sales,
    )
    return {
        "impressions": metric.impressions,
        "top_of_search_share": _decimal_string(
            getattr(metric, "top_of_search_share", None)
        ),
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


def _overview_item_payload(
    *, metric, remote_scope, currency_code: str
) -> dict[str, object]:
    partial_fields = ["topOfSearchShare", "ordersAttributionWindow"]
    if metric.start_date is None:
        partial_fields.append("startDate")
    if not metric.has_metrics:
        partial_fields.extend(
            [
                "impressions",
                "spend",
                "sales",
                "clicks",
                "ctr",
                "totalCost",
                "orders",
                "cpc",
                "acos",
                "cvr",
            ]
        )
    if not metric.scm_matched:
        partial_fields.extend(
            [
                "referenceCode",
                "targetingType",
                "biddingStrategy",
                "endDate",
            ]
        )
    return {
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
        "metrics": _metric_payload(metric=metric, currency_code=currency_code),
        "metadata_matched": metric.scm_matched,
        "has_metrics": metric.has_metrics,
        "partial_fields": sorted(set(partial_fields)),
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
        metric_filters=query.get("metric_filters", ()),
        ordering=query.get("ordering", "-spend"),
        page=query.get("page", 1),
        page_size=query.get("page_size", 15),
        include_summary=query.get("include_summary", True),
        require_metrics=bool(query.get("start_date") and query.get("end_date"))
        or bool(query.get("metric_filters")),
    )
    currency_code = scope.profile.currency_code
    items = [
        _overview_item_payload(
            metric=metric,
            remote_scope=remote_scope,
            currency_code=currency_code,
        )
        for metric in result.items
    ]

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
            "source": "REMOTE_MYSQL_COMPOSITE",
            "currency_code": currency_code,
            "timezone": scope.profile.timezone,
            "start_date": result.start_date,
            "end_date": result.end_date,
            "data_through_date": result.data_through_date,
            "history_through_date": result.history_through_date,
            "realtime_through_date": result.realtime_through_date,
            "realtime_as_of": result.realtime_as_of,
            "deduplication_version": result.deduplication_version,
            "field_mappings": result.field_mappings or {},
            "total_cost_semantics": "SPEND_ALIAS",
            "attribution_semantics": "REMOTE_FIELDS_UNVERIFIED",
            "status_filter_semantics": "SCM_CURRENT_STATE_WITH_FACT_FALLBACK",
        },
    }


def campaign_detail_page(
    *,
    user,
    tenant_id,
    profile_id,
    campaign_key: str,
    start_date=None,
    end_date=None,
) -> dict[str, object]:
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="advertising.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    remote_scope = remote_scope_for_profile(scope.profile)
    raw_key = _raw_campaign_key(
        remote_scope.merchant_id,
        remote_scope.merchant_code,
        campaign_key,
    )
    result = RemoteAdvertisingDataReader().campaign_detail(
        merchant_id=remote_scope.merchant_id,
        merchant_code=remote_scope.merchant_code,
        campaign_key=raw_key,
        start_date=start_date,
        end_date=end_date,
    )
    if not result.items:
        raise NotFound("广告活动不存在")
    currency_code = scope.profile.currency_code
    return {
        "item": _overview_item_payload(
            metric=result.items[0],
            remote_scope=remote_scope,
            currency_code=currency_code,
        ),
        "trend": [
            {
                "date": item.report_date,
                "metrics": _metric_payload(metric=item, currency_code=currency_code),
            }
            for item in result.trend
        ],
        "meta": {
            "source": "REMOTE_MYSQL_COMPOSITE",
            "currency_code": currency_code,
            "timezone": scope.profile.timezone,
            "start_date": result.start_date,
            "end_date": result.end_date,
            "data_through_date": result.data_through_date,
            "history_through_date": result.history_through_date,
            "realtime_through_date": result.realtime_through_date,
            "realtime_as_of": result.realtime_as_of,
            "deduplication_version": result.deduplication_version,
            "field_mappings": result.field_mappings or {},
            "total_cost_semantics": "SPEND_ALIAS",
            "attribution_semantics": "REMOTE_FIELDS_UNVERIFIED",
            "status_filter_semantics": "SCM_CURRENT_STATE_WITH_FACT_FALLBACK",
        },
    }


def update_campaign_enabled_state(
    *,
    request,
    user,
    tenant_id,
    profile_id,
    campaign_key: str,
    enabled: bool,
    start_date=None,
    end_date=None,
) -> dict[str, object]:
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="advertising.view",
        minimum_level=ProfileAccessLevel.OPERATE,
    )
    remote_scope = remote_scope_for_profile(scope.profile)
    raw_campaign_key = _raw_campaign_key(
        remote_scope.merchant_id,
        remote_scope.merchant_code,
        campaign_key,
    )
    reader = RemoteAdvertisingDataReader()
    current = reader.campaign_detail(
        merchant_id=remote_scope.merchant_id,
        merchant_code=remote_scope.merchant_code,
        campaign_key=raw_campaign_key,
        start_date=start_date,
        end_date=end_date,
    )
    if not current.items:
        raise NotFound("广告活动不存在")
    current_item = current.items[0]
    updated = reader.update_campaign_enabled(
        merchant_id=remote_scope.merchant_id,
        merchant_code=remote_scope.merchant_code,
        campaign_key=raw_campaign_key,
        enabled=enabled,
        campaign_name=current_item.campaign_name,
        targeting_type=current_item.targeting_type,
        daily_budget=current_item.daily_budget,
        bidding_strategy=current_item.bidding_strategy,
        start_date=current_item.start_date,
        end_date=current_item.end_date,
        actor_id=getattr(user, "pk", None),
        actor_name=getattr(user, "email", "") or getattr(user, "username", ""),
    )
    if not updated:
        raise NotFound("广告活动不存在")
    append_audit_log(
        request=request,
        tenant=scope.membership.tenant,
        actor=user,
        event="campaign.enabled_updated",
        object_type="RemoteCampaign",
        object_id=raw_campaign_key,
        after_data={"enabled": enabled},
        metadata={
            "source": "REMOTE_MYSQL_SCM",
            "merchant_id": remote_scope.merchant_id,
            "merchant_code": remote_scope.merchant_code,
        },
    )

    result = reader.campaign_detail(
        merchant_id=remote_scope.merchant_id,
        merchant_code=remote_scope.merchant_code,
        campaign_key=raw_campaign_key,
        start_date=start_date,
        end_date=end_date,
    )
    if not result.items:
        raise NotFound("广告活动不存在")
    return {
        "item": _overview_item_payload(
            metric=result.items[0],
            remote_scope=remote_scope,
            currency_code=scope.profile.currency_code,
        )
    }


def create_remote_campaign(
    *,
    request,
    user,
    tenant_id,
    profile_id,
    name: str,
    targeting_type: str,
    daily_budget: Decimal,
    bidding_strategy: str,
    start_date,
    end_date=None,
    enabled: bool = True,
) -> dict[str, object]:
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="advertising.view",
        minimum_level=ProfileAccessLevel.OPERATE,
    )
    remote_scope = remote_scope_for_profile(scope.profile)
    reader = RemoteAdvertisingDataReader()
    raw_campaign_key = reader.create_campaign(
        merchant_id=remote_scope.merchant_id,
        merchant_code=remote_scope.merchant_code,
        name=name,
        targeting_type=targeting_type,
        daily_budget=daily_budget,
        bidding_strategy=bidding_strategy,
        start_date=start_date,
        end_date=end_date,
        enabled=enabled,
        actor_id=getattr(user, "pk", None),
        actor_name=getattr(user, "email", "") or getattr(user, "username", ""),
    )
    append_audit_log(
        request=request,
        tenant=scope.membership.tenant,
        actor=user,
        event="campaign.created",
        object_type="RemoteCampaign",
        object_id=raw_campaign_key,
        after_data={
            "name": name,
            "targeting_type": targeting_type,
            "daily_budget": str(daily_budget),
            "bidding_strategy": bidding_strategy,
            "start_date": str(start_date),
            "end_date": str(end_date) if end_date else None,
            "enabled": enabled,
        },
        metadata={
            "source": "REMOTE_MYSQL_SCM",
            "merchant_id": remote_scope.merchant_id,
            "merchant_code": remote_scope.merchant_code,
        },
    )
    result = reader.campaign_detail(
        merchant_id=remote_scope.merchant_id,
        merchant_code=remote_scope.merchant_code,
        campaign_key=raw_campaign_key,
        start_date=start_date,
        end_date=end_date or start_date,
    )
    if not result.items:
        raise NotFound("广告活动创建后未能读取")
    return {
        "item": _overview_item_payload(
            metric=result.items[0],
            remote_scope=remote_scope,
            currency_code=scope.profile.currency_code,
        )
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
