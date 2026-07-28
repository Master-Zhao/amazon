import hashlib
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import NotFound
from rest_framework.serializers import ValidationError

from apps.advertising.models import (
    AdGroup,
    Campaign,
    Keyword,
    ProductTarget,
    SearchTerm,
)
from apps.audit.services import append_audit_log
from apps.permissions.models import ProfileAccessLevel
from apps.permissions.services import require_profile_scope
from apps.analytics.models import (
    AnomalyRecord,
    AnomalyRuleCode,
    AnomalyRuleVersion,
    AnomalyStatus,
    CampaignDailyMetric,
    CampaignMetricRevision,
    RiskLevel,
    SearchTermDailyMetric,
    SearchTermMetricRevision,
    TargetingDailyMetric,
    TargetingMetricRevision,
)


SYSTEM_RULES: dict[str, dict[str, str | int]] = {
    AnomalyRuleCode.HIGH_ACOS: {
        "minimum_clicks": 10,
        "minimum_sales": "0.01",
    },
    AnomalyRuleCode.HIGH_SPEND_NO_ORDERS: {
        "minimum_spend": "30.00",
    },
    AnomalyRuleCode.HIGH_CLICKS_LOW_CONVERSION: {
        "minimum_clicks": 20,
        "maximum_cvr": "0.02",
    },
    AnomalyRuleCode.BUDGET_EARLY_EXHAUSTION: {
        "minimum_budget_usage_ratio": "0.90",
        "latest_early_hour": 18,
    },
    AnomalyRuleCode.LOW_IMPRESSIONS: {
        "minimum_impressions": 100,
    },
    AnomalyRuleCode.LOW_CLICKS: {
        "minimum_clicks": 5,
    },
}


def safe_ratio(
    numerator: Decimal | int,
    denominator: Decimal | int,
    *,
    zero_reason: str,
) -> tuple[Decimal | None, str | None]:
    numerator_value = Decimal(str(numerator))
    denominator_value = Decimal(str(denominator))
    if denominator_value == 0:
        return None, zero_reason
    return numerator_value / denominator_value, None


def metric_formulas(
    *,
    impressions: int,
    clicks: int,
    spend: Decimal,
    orders: int,
    sales: Decimal,
) -> dict[str, dict[str, Decimal | str | None]]:
    ctr, ctr_reason = safe_ratio(clicks, impressions, zero_reason="NO_IMPRESSIONS")
    cpc, cpc_reason = safe_ratio(spend, clicks, zero_reason="NO_CLICKS")
    cvr, cvr_reason = safe_ratio(orders, clicks, zero_reason="NO_CLICKS")
    acos, acos_reason = safe_ratio(spend, sales, zero_reason="NO_SALES")
    roas, roas_reason = safe_ratio(sales, spend, zero_reason="NO_SPEND")
    return {
        "ctr": {"value": ctr, "reason": ctr_reason},
        "cpc": {"value": cpc, "reason": cpc_reason},
        "cvr": {"value": cvr, "reason": cvr_reason},
        "acos": {"value": acos, "reason": acos_reason},
        "roas": {"value": roas, "reason": roas_reason},
    }


def metric_calculation_reasons(
    *,
    impressions: int,
    clicks: int,
    spend: Decimal,
    orders: int,
    sales: Decimal,
) -> dict[str, str]:
    return {
        name: str(item["reason"])
        for name, item in metric_formulas(
            impressions=impressions,
            clicks=clicks,
            spend=spend,
            orders=orders,
            sales=sales,
        ).items()
        if item["reason"] is not None
    }


def resolve_target_acos(campaign: Campaign) -> Decimal | None:
    if campaign.target_acos is not None:
        return campaign.target_acos
    if campaign.profile.target_acos is not None:
        return campaign.profile.target_acos
    return campaign.profile.store_marketplace.store.tenant.target_acos


def _validated_target_acos(value: Decimal | None) -> Decimal | None:
    if value is not None and (value <= 0 or value > 10):
        raise ValidationError(
            {"target_acos": ["Target ACOS must be greater than 0 and at most 10."]}
        )
    return value


@transaction.atomic
def set_target_acos(
    *,
    request,
    tenant_id,
    profile_id,
    scope_type: str,
    target_acos: Decimal | None,
    campaign_id=None,
):
    scope = require_profile_scope(
        user=request.user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="analytics.configure",
        minimum_level=ProfileAccessLevel.MANAGE,
    )
    value = _validated_target_acos(target_acos)
    normalized_scope = scope_type.upper()
    if normalized_scope == "TENANT":
        target = scope.membership.tenant
    elif normalized_scope == "PROFILE":
        target = scope.profile
    elif normalized_scope == "CAMPAIGN":
        target = Campaign.objects.select_for_update().filter(
            pk=campaign_id,
            profile=scope.profile,
        ).first()
        if target is None:
            raise NotFound("Campaign does not exist in the current Profile scope.")
    else:
        raise ValidationError(
            {"scope_type": ["Use TENANT, PROFILE or CAMPAIGN."]}
        )
    previous = target.target_acos
    target.target_acos = value
    target.save(update_fields=["target_acos"])
    append_audit_log(
        request=request,
        tenant=scope.membership.tenant,
        actor=request.user,
        event="analytics.target_acos_configured",
        object_type=target.__class__.__name__,
        object_id=target.pk,
        before_data={
            "scope_type": normalized_scope,
            "target_acos": str(previous) if previous is not None else None,
        },
        after_data={
            "scope_type": normalized_scope,
            "target_acos": str(value) if value is not None else None,
        },
    )
    return target


def _validate_rule_configuration(
    *,
    code: str,
    configuration: dict[str, object],
) -> dict[str, str | int]:
    if code not in SYSTEM_RULES:
        raise ValidationError({"code": ["Unsupported anomaly rule code."]})
    unknown = set(configuration) - set(SYSTEM_RULES[code])
    if unknown:
        raise ValidationError(
            {"configuration": [f"Unknown keys: {', '.join(sorted(unknown))}."]}
        )
    result = dict(SYSTEM_RULES[code])
    result.update(configuration)
    for key, raw_value in result.items():
        if key in {"minimum_clicks", "minimum_impressions", "latest_early_hour"}:
            try:
                value = int(raw_value)
            except (TypeError, ValueError) as exc:
                raise ValidationError(
                    {"configuration": [f"{key} must be an integer."]}
                ) from exc
            if value < 0 or (key == "latest_early_hour" and value > 23):
                raise ValidationError(
                    {"configuration": [f"{key} is outside the allowed range."]}
                )
            result[key] = value
        else:
            try:
                value = Decimal(str(raw_value))
            except Exception as exc:
                raise ValidationError(
                    {"configuration": [f"{key} must be a decimal number."]}
                ) from exc
            if value < 0:
                raise ValidationError(
                    {"configuration": [f"{key} cannot be negative."]}
                )
            if key in {"maximum_cvr", "minimum_budget_usage_ratio"} and value > 1:
                raise ValidationError(
                    {"configuration": [f"{key} cannot exceed 1."]}
                )
            result[key] = format(value, "f")
    return result


@transaction.atomic
def create_anomaly_rule_version(
    *,
    request,
    tenant_id,
    profile_id,
    code: str,
    scope_type: str,
    configuration: dict[str, object],
    campaign_id=None,
) -> AnomalyRuleVersion:
    scope = require_profile_scope(
        user=request.user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="analytics.configure",
        minimum_level=ProfileAccessLevel.MANAGE,
    )
    normalized_scope = scope_type.upper()
    relation_values = {"tenant": None, "profile": None, "campaign": None}
    if normalized_scope == "TENANT":
        scope_key = f"TENANT:{scope.membership.tenant_id}"
        relation_values["tenant"] = scope.membership.tenant
    elif normalized_scope == "PROFILE":
        scope_key = f"PROFILE:{scope.profile.pk}"
        relation_values["profile"] = scope.profile
    elif normalized_scope == "CAMPAIGN":
        campaign = Campaign.objects.filter(
            pk=campaign_id,
            profile=scope.profile,
        ).first()
        if campaign is None:
            raise NotFound("Campaign does not exist in the current Profile scope.")
        scope_key = f"CAMPAIGN:{campaign.pk}"
        relation_values["campaign"] = campaign
    else:
        raise ValidationError(
            {"scope_type": ["Use TENANT, PROFILE or CAMPAIGN."]}
        )
    validated = _validate_rule_configuration(
        code=code,
        configuration=configuration,
    )
    latest_version = (
        AnomalyRuleVersion.objects.filter(code=code, scope_key=scope_key).aggregate(
            value=Max("version")
        )["value"]
        or 0
    )
    rule = AnomalyRuleVersion.objects.create(
        code=code,
        version=latest_version + 1,
        scope_key=scope_key,
        configuration=validated,
        **relation_values,
    )
    append_audit_log(
        request=request,
        tenant=scope.membership.tenant,
        actor=request.user,
        event="analytics.rule_version_created",
        object_type="AnomalyRuleVersion",
        object_id=rule.pk,
        after_data={
            "code": rule.code,
            "version": rule.version,
            "scope_key": rule.scope_key,
            "configuration": rule.configuration,
        },
    )
    return rule


def ensure_system_rules() -> dict[str, AnomalyRuleVersion]:
    result: dict[str, AnomalyRuleVersion] = {}
    for code, configuration in SYSTEM_RULES.items():
        rule, _ = AnomalyRuleVersion.objects.get_or_create(
            code=code,
            version=1,
            scope_key="SYSTEM",
            defaults={"configuration": configuration},
        )
        result[code] = rule
    return result


def resolve_rule(
    *,
    code: str,
    campaign: Campaign,
    system_rule: AnomalyRuleVersion,
) -> AnomalyRuleVersion:
    candidates = (
        AnomalyRuleVersion.objects.filter(
            code=code,
            is_active=True,
        )
        .exclude(scope_key="SYSTEM")
        .filter(
            models_filter_for_campaign(campaign)
        )
        .order_by("-version", "-created_at")
    )
    for scope_key in (
        f"CAMPAIGN:{campaign.pk}",
        f"PROFILE:{campaign.profile_id}",
        f"TENANT:{campaign.profile.store_marketplace.store.tenant_id}",
    ):
        match = candidates.filter(scope_key=scope_key).first()
        if match:
            return match
    return system_rule


def models_filter_for_campaign(campaign: Campaign):
    from django.db.models import Q

    return (
        Q(campaign=campaign)
        | Q(profile=campaign.profile)
        | Q(tenant=campaign.profile.store_marketplace.store.tenant)
    )


def _record(
    *,
    metric: CampaignDailyMetric,
    rule: AnomalyRuleVersion,
    status: str,
    risk_level: str | None,
    observed_value: Decimal | None,
    threshold_value: Decimal | None,
    reason_code: str,
    explanation: str,
) -> AnomalyRecord:
    return AnomalyRecord.objects.create(
        metric=metric,
        rule_version=rule,
        source_batch=metric.source_batch,
        status=status,
        risk_level=risk_level,
        observed_value=observed_value,
        threshold_value=threshold_value,
        reason_code=reason_code,
        explanation=explanation,
    )


def evaluate_metric_anomalies(metric: CampaignDailyMetric) -> list[AnomalyRecord]:
    campaign = metric.campaign
    system_rules = ensure_system_rules()
    formulas = metric_formulas(
        impressions=metric.impressions,
        clicks=metric.clicks,
        spend=metric.spend,
        orders=metric.orders,
        sales=metric.sales,
    )
    records: list[AnomalyRecord] = []

    high_acos_rule = resolve_rule(
        code=AnomalyRuleCode.HIGH_ACOS,
        campaign=campaign,
        system_rule=system_rules[AnomalyRuleCode.HIGH_ACOS],
    )
    target = resolve_target_acos(campaign)
    acos = formulas["acos"]["value"]
    min_clicks = int(high_acos_rule.configuration["minimum_clicks"])
    min_sales = Decimal(str(high_acos_rule.configuration["minimum_sales"]))
    if target is None:
        records.append(
            _record(
                metric=metric,
                rule=high_acos_rule,
                status=AnomalyStatus.INSUFFICIENT_DATA,
                risk_level=None,
                observed_value=acos if isinstance(acos, Decimal) else None,
                threshold_value=None,
                reason_code="NO_TARGET_ACOS",
                explanation="No Campaign, Profile or Tenant target ACOS is configured.",
            )
        )
    elif metric.clicks < min_clicks or metric.sales < min_sales or acos is None:
        records.append(
            _record(
                metric=metric,
                rule=high_acos_rule,
                status=AnomalyStatus.INSUFFICIENT_DATA,
                risk_level=None,
                observed_value=acos if isinstance(acos, Decimal) else None,
                threshold_value=target,
                reason_code="MINIMUM_DATA_NOT_MET",
                explanation=(
                    f"High ACOS requires at least {min_clicks} clicks and "
                    f"{min_sales} sales."
                ),
            )
        )
    else:
        is_anomaly = acos > target
        ratio_to_target = acos / target if target else Decimal("0")
        risk = (
            RiskLevel.HIGH
            if is_anomaly and ratio_to_target >= Decimal("1.5")
            else RiskLevel.MEDIUM if is_anomaly else None
        )
        records.append(
            _record(
                metric=metric,
                rule=high_acos_rule,
                status=AnomalyStatus.ANOMALY if is_anomaly else AnomalyStatus.NORMAL,
                risk_level=risk,
                observed_value=acos,
                threshold_value=target,
                reason_code="ACOS_ABOVE_TARGET" if is_anomaly else "",
                explanation=(
                    f"ACOS {acos:.4f} is "
                    f"{'above' if is_anomaly else 'within'} target {target:.4f}."
                ),
            )
        )

    spend_rule = resolve_rule(
        code=AnomalyRuleCode.HIGH_SPEND_NO_ORDERS,
        campaign=campaign,
        system_rule=system_rules[AnomalyRuleCode.HIGH_SPEND_NO_ORDERS],
    )
    spend_threshold = Decimal(str(spend_rule.configuration["minimum_spend"]))
    spend_anomaly = metric.spend >= spend_threshold and metric.orders == 0
    records.append(
        _record(
            metric=metric,
            rule=spend_rule,
            status=AnomalyStatus.ANOMALY if spend_anomaly else AnomalyStatus.NORMAL,
            risk_level=RiskLevel.HIGH if spend_anomaly else None,
            observed_value=metric.spend,
            threshold_value=spend_threshold,
            reason_code="SPEND_WITHOUT_ORDERS" if spend_anomaly else "",
            explanation=(
                f"Spend is {metric.spend:.4f}; orders are {metric.orders}; "
                f"threshold is {spend_threshold:.4f}."
            ),
        )
    )

    conversion_rule = resolve_rule(
        code=AnomalyRuleCode.HIGH_CLICKS_LOW_CONVERSION,
        campaign=campaign,
        system_rule=system_rules[AnomalyRuleCode.HIGH_CLICKS_LOW_CONVERSION],
    )
    conversion_clicks = int(conversion_rule.configuration["minimum_clicks"])
    maximum_cvr = Decimal(str(conversion_rule.configuration["maximum_cvr"]))
    cvr = formulas["cvr"]["value"]
    if metric.clicks < conversion_clicks or cvr is None:
        conversion_status = AnomalyStatus.INSUFFICIENT_DATA
        conversion_risk = None
        conversion_reason = "MINIMUM_DATA_NOT_MET"
    else:
        conversion_status = (
            AnomalyStatus.ANOMALY if cvr < maximum_cvr else AnomalyStatus.NORMAL
        )
        conversion_risk = (
            RiskLevel.MEDIUM
            if conversion_status == AnomalyStatus.ANOMALY
            else None
        )
        conversion_reason = (
            "CVR_BELOW_THRESHOLD"
            if conversion_status == AnomalyStatus.ANOMALY
            else ""
        )
    records.append(
        _record(
            metric=metric,
            rule=conversion_rule,
            status=conversion_status,
            risk_level=conversion_risk,
            observed_value=cvr if isinstance(cvr, Decimal) else None,
            threshold_value=maximum_cvr,
            reason_code=conversion_reason,
            explanation=(
                f"CVR is {cvr if cvr is not None else 'unavailable'}; "
                f"minimum clicks are {conversion_clicks}."
            ),
        )
    )

    budget_rule = resolve_rule(
        code=AnomalyRuleCode.BUDGET_EARLY_EXHAUSTION,
        campaign=campaign,
        system_rule=system_rules[AnomalyRuleCode.BUDGET_EARLY_EXHAUSTION],
    )
    budget_ratio_threshold = Decimal(
        str(budget_rule.configuration["minimum_budget_usage_ratio"])
    )
    latest_early_hour = int(budget_rule.configuration["latest_early_hour"])
    if (
        metric.daily_budget_snapshot is None
        or metric.daily_budget_snapshot == 0
        or metric.snapshot_hour_local is None
    ):
        budget_status = AnomalyStatus.INSUFFICIENT_DATA
        budget_risk = None
        budget_observed = None
        budget_reason = "NO_INTRADAY_BUDGET_SNAPSHOT"
    else:
        budget_observed = metric.spend / metric.daily_budget_snapshot
        early_exhaustion = (
            metric.snapshot_hour_local <= latest_early_hour
            and budget_observed >= budget_ratio_threshold
            and metric.state_snapshot == "ENABLED"
        )
        budget_status = (
            AnomalyStatus.ANOMALY
            if early_exhaustion
            else AnomalyStatus.NORMAL
        )
        budget_risk = RiskLevel.HIGH if early_exhaustion else None
        budget_reason = "BUDGET_EXHAUSTED_EARLY" if early_exhaustion else ""
    records.append(
        _record(
            metric=metric,
            rule=budget_rule,
            status=budget_status,
            risk_level=budget_risk,
            observed_value=budget_observed,
            threshold_value=budget_ratio_threshold,
            reason_code=budget_reason,
            explanation=(
                "Budget usage is "
                f"{budget_observed if budget_observed is not None else 'unavailable'}; "
                f"local snapshot hour is {metric.snapshot_hour_local}; "
                f"early-hour boundary is {latest_early_hour}."
            ),
        )
    )

    impressions_rule = resolve_rule(
        code=AnomalyRuleCode.LOW_IMPRESSIONS,
        campaign=campaign,
        system_rule=system_rules[AnomalyRuleCode.LOW_IMPRESSIONS],
    )
    impression_threshold = int(
        impressions_rule.configuration["minimum_impressions"]
    )
    impression_anomaly = metric.impressions < impression_threshold
    records.append(
        _record(
            metric=metric,
            rule=impressions_rule,
            status=(
                AnomalyStatus.ANOMALY
                if impression_anomaly
                else AnomalyStatus.NORMAL
            ),
            risk_level=RiskLevel.LOW if impression_anomaly else None,
            observed_value=Decimal(metric.impressions),
            threshold_value=Decimal(impression_threshold),
            reason_code="IMPRESSIONS_BELOW_THRESHOLD" if impression_anomaly else "",
            explanation=(
                f"Impressions are {metric.impressions}; "
                f"threshold is {impression_threshold}."
            ),
        )
    )
    clicks_rule = resolve_rule(
        code=AnomalyRuleCode.LOW_CLICKS,
        campaign=campaign,
        system_rule=system_rules[AnomalyRuleCode.LOW_CLICKS],
    )
    click_threshold = int(clicks_rule.configuration["minimum_clicks"])
    click_anomaly = metric.clicks < click_threshold
    records.append(
        _record(
            metric=metric,
            rule=clicks_rule,
            status=AnomalyStatus.ANOMALY if click_anomaly else AnomalyStatus.NORMAL,
            risk_level=RiskLevel.LOW if click_anomaly else None,
            observed_value=Decimal(metric.clicks),
            threshold_value=Decimal(click_threshold),
            reason_code="CLICKS_BELOW_THRESHOLD" if click_anomaly else "",
            explanation=(
                f"Clicks are {metric.clicks}; threshold is {click_threshold}."
            ),
        )
    )
    return records


@transaction.atomic
def recalculate_profile_anomalies(profile_id) -> int:
    metrics = CampaignDailyMetric.objects.filter(
        profile_id=profile_id,
    ).select_related(
        "campaign__profile__store_marketplace__store__tenant",
        "source_batch",
    )
    processed = 0
    for metric in metrics.iterator():
        evaluate_metric_anomalies(metric)
        processed += 1
    return processed


def _metric_values(metric: CampaignDailyMetric) -> dict[str, object]:
    return {
        "currency_code": metric.currency_code,
        "impressions": metric.impressions,
        "clicks": metric.clicks,
        "spend": str(metric.spend),
        "orders": metric.orders,
        "sales": str(metric.sales),
        "calculation_reasons": metric.calculation_reasons,
        "daily_budget_snapshot": (
            str(metric.daily_budget_snapshot)
            if metric.daily_budget_snapshot is not None
            else None
        ),
        "snapshot_hour_local": metric.snapshot_hour_local,
        "state_snapshot": metric.state_snapshot,
        "source_batch_id": metric.source_batch_id,
    }


@transaction.atomic
def publish_campaign_metrics(*, batch, rows: list[dict[str, object]]) -> list[CampaignDailyMetric]:
    campaign_map = {
        campaign.external_campaign_id: campaign
        for campaign in Campaign.objects.select_related(
            "profile__store_marketplace__store__tenant"
        ).filter(
            profile=batch.task.upload.profile,
            external_campaign_id__in=[row["campaign_id"] for row in rows],
        )
    }
    published: list[CampaignDailyMetric] = []
    for row in rows:
        campaign = campaign_map[str(row["campaign_id"])]
        report_date = date.fromisoformat(str(row["date"]))
        metric = (
            CampaignDailyMetric.objects.select_for_update()
            .filter(
                profile=batch.task.upload.profile,
                campaign=campaign,
                report_date=report_date,
            )
            .first()
        )
        defaults = {
            "currency_code": row["currency"],
            "impressions": row["impressions"],
            "clicks": row["clicks"],
            "spend": Decimal(str(row["spend"])),
            "orders": row["orders"],
            "sales": Decimal(str(row["sales"])),
            "calculation_reasons": metric_calculation_reasons(
                impressions=int(row["impressions"]),
                clicks=int(row["clicks"]),
                spend=Decimal(str(row["spend"])),
                orders=int(row["orders"]),
                sales=Decimal(str(row["sales"])),
            ),
            "daily_budget_snapshot": (
                Decimal(str(row["daily_budget"]))
                if row["daily_budget"] is not None
                else None
            ),
            "snapshot_hour_local": row["snapshot_hour_local"],
            "state_snapshot": row["campaign_status"],
            "source_batch": batch,
        }
        previous_values: dict[str, object] = {}
        if metric is None:
            metric = CampaignDailyMetric.objects.create(
                profile=batch.task.upload.profile,
                campaign=campaign,
                report_date=report_date,
                **defaults,
            )
        else:
            previous_values = _metric_values(metric)
            for field, value in defaults.items():
                setattr(metric, field, value)
            metric.save(
                update_fields=[
                    *defaults.keys(),
                    "updated_at",
                ]
            )
        CampaignMetricRevision.objects.create(
            metric=metric,
            source_batch=batch,
            previous_values=previous_values,
            current_values=_metric_values(metric),
        )
        evaluate_metric_anomalies(metric)
        published.append(metric)
    return published


def _base_metric_values(metric) -> dict[str, object]:
    return {
        "currency_code": metric.currency_code,
        "impressions": metric.impressions,
        "clicks": metric.clicks,
        "spend": str(metric.spend),
        "orders": metric.orders,
        "sales": str(metric.sales),
        "calculation_reasons": metric.calculation_reasons,
        "source_batch_id": metric.source_batch_id,
    }


@transaction.atomic
def publish_targeting_metrics(
    *,
    batch,
    rows: list[dict[str, object]],
) -> list[TargetingDailyMetric]:
    profile = batch.task.upload.profile
    ad_groups = {
        (item.campaign.external_campaign_id, item.external_ad_group_id): item
        for item in AdGroup.objects.select_related("campaign").filter(
            campaign__profile=profile,
            external_ad_group_id__in={
                str(row["ad_group_id"]) for row in rows
            },
        )
    }
    keyword_rows = [row for row in rows if row["target_type"] == "KEYWORD"]
    keywords = {
        (item.ad_group_id, item.external_keyword_id): item
        for item in Keyword.objects.filter(
            ad_group__campaign__profile=profile,
            external_keyword_id__in={
                str(row["target_id"]) for row in keyword_rows
            },
        )
    }
    product_rows = [
        row for row in rows if row["target_type"] == "PRODUCT_TARGET"
    ]
    product_targets = {
        (item.ad_group_id, item.external_target_id): item
        for item in ProductTarget.objects.filter(
            ad_group__campaign__profile=profile,
            external_target_id__in={
                str(row["target_id"]) for row in product_rows
            },
        )
    }

    prepared: list[tuple[dict[str, object], AdGroup, object, str]] = []
    for row in rows:
        ad_group = ad_groups[
            (str(row["campaign_id"]), str(row["ad_group_id"]))
        ]
        if row["target_type"] == "KEYWORD":
            entity = keywords[(ad_group.pk, str(row["target_id"]))]
        else:
            entity = product_targets[(ad_group.pk, str(row["target_id"]))]
        target_key = f"{row['target_type']}:{entity.pk}"
        prepared.append((row, ad_group, entity, target_key))

    report_dates = {
        date.fromisoformat(str(row["date"])) for row, _, _, _ in prepared
    }
    target_keys = {target_key for _, _, _, target_key in prepared}
    prepared_keys = {
        (target_key, date.fromisoformat(str(row["date"])))
        for row, _, _, target_key in prepared
    }
    existing = {
        (item.target_key, item.report_date): item
        for item in TargetingDailyMetric.objects.select_for_update().filter(
            profile=profile,
            target_key__in=target_keys,
            report_date__in=report_dates,
        )
    }
    previous_by_key: dict[tuple[str, date], dict[str, object]] = {}
    new_metrics: list[TargetingDailyMetric] = []
    changed_metrics: list[TargetingDailyMetric] = []
    for row, ad_group, entity, target_key in prepared:
        report_date = date.fromisoformat(str(row["date"]))
        key = (target_key, report_date)
        metric = existing.get(key)
        defaults = {
            "campaign": ad_group.campaign,
            "ad_group": ad_group,
            "target_type": str(row["target_type"]),
            "target_key": target_key,
            "keyword": entity if row["target_type"] == "KEYWORD" else None,
            "product_target": (
                entity if row["target_type"] == "PRODUCT_TARGET" else None
            ),
            "currency_code": str(row["currency"]),
            "impressions": int(row["impressions"]),
            "clicks": int(row["clicks"]),
            "spend": Decimal(str(row["spend"])),
            "orders": int(row["orders"]),
            "sales": Decimal(str(row["sales"])),
            "calculation_reasons": metric_calculation_reasons(
                impressions=int(row["impressions"]),
                clicks=int(row["clicks"]),
                spend=Decimal(str(row["spend"])),
                orders=int(row["orders"]),
                sales=Decimal(str(row["sales"])),
            ),
            "bid_snapshot": (
                Decimal(str(row["bid"])) if row["bid"] is not None else None
            ),
            "state_snapshot": str(row["target_status"]),
            "source_batch": batch,
        }
        if metric is None:
            new_metrics.append(
                TargetingDailyMetric(
                    profile=profile,
                    report_date=report_date,
                    **defaults,
                )
            )
        else:
            previous_by_key[key] = {
                **_base_metric_values(metric),
                "bid_snapshot": (
                    str(metric.bid_snapshot)
                    if metric.bid_snapshot is not None
                    else None
                ),
                "state_snapshot": metric.state_snapshot,
            }
            for field, value in defaults.items():
                setattr(metric, field, value)
            changed_metrics.append(metric)
    if new_metrics:
        TargetingDailyMetric.objects.bulk_create(new_metrics)
    if changed_metrics:
        TargetingDailyMetric.objects.bulk_update(
            changed_metrics,
            [
                "campaign",
                "ad_group",
                "target_type",
                "keyword",
                "product_target",
                "currency_code",
                "impressions",
                "clicks",
                "spend",
                "orders",
                "sales",
                "calculation_reasons",
                "bid_snapshot",
                "state_snapshot",
                "source_batch",
                "updated_at",
            ],
        )
    published = [
        metric
        for metric in TargetingDailyMetric.objects.filter(
            profile=profile,
            target_key__in=target_keys,
            report_date__in=report_dates,
        )
        if (metric.target_key, metric.report_date) in prepared_keys
    ]
    revisions = []
    for metric in published:
        key = (metric.target_key, metric.report_date)
        revisions.append(
            TargetingMetricRevision(
                metric=metric,
                source_batch=batch,
                previous_values=previous_by_key.get(key, {}),
                current_values={
                    **_base_metric_values(metric),
                    "bid_snapshot": (
                        str(metric.bid_snapshot)
                        if metric.bid_snapshot is not None
                        else None
                    ),
                    "state_snapshot": metric.state_snapshot,
                },
            )
        )
    TargetingMetricRevision.objects.bulk_create(revisions)
    return published


@transaction.atomic
def publish_search_term_metrics(
    *,
    batch,
    rows: list[dict[str, object]],
) -> list[SearchTermDailyMetric]:
    profile = batch.task.upload.profile
    campaigns = {
        item.external_campaign_id: item
        for item in Campaign.objects.filter(
            profile=profile,
            external_campaign_id__in={
                str(row["campaign_id"]) for row in rows
            },
        )
    }
    ad_groups = {
        (item.campaign_id, item.external_ad_group_id): item
        for item in AdGroup.objects.filter(
            campaign__profile=profile,
            external_ad_group_id__in={
                str(row["ad_group_id"]) for row in rows
            },
        )
    }
    search_terms = {
        item.text_hash: item
        for item in SearchTerm.objects.filter(
            profile=profile,
            text_hash__in={str(row["search_term_hash"]) for row in rows},
        )
    }
    prepared = []
    for row in rows:
        campaign = campaigns[str(row["campaign_id"])]
        ad_group = ad_groups[(campaign.pk, str(row["ad_group_id"]))]
        search_term = search_terms[str(row["search_term_hash"])]
        expression = " ".join(str(row["targeting_expression"]).split())
        expression_hash = hashlib.sha256(
            expression.casefold().encode("utf-8")
        ).hexdigest()
        key = (
            campaign.pk,
            ad_group.pk,
            search_term.pk,
            date.fromisoformat(str(row["date"])),
            expression_hash,
        )
        prepared.append(
            (row, campaign, ad_group, search_term, expression, expression_hash, key)
        )
    dates = {item[6][3] for item in prepared}
    expression_hashes = {item[5] for item in prepared}
    prepared_keys = {item[6] for item in prepared}
    existing = {
        (
            item.campaign_id,
            item.ad_group_id,
            item.search_term_id,
            item.report_date,
            item.targeting_expression_hash,
        ): item
        for item in SearchTermDailyMetric.objects.select_for_update().filter(
            profile=profile,
            report_date__in=dates,
            targeting_expression_hash__in=expression_hashes,
        )
    }
    previous_by_key: dict[tuple, dict[str, object]] = {}
    new_metrics: list[SearchTermDailyMetric] = []
    changed_metrics: list[SearchTermDailyMetric] = []
    for row, campaign, ad_group, search_term, expression, expression_hash, key in prepared:
        metric = existing.get(key)
        defaults = {
            "currency_code": str(row["currency"]),
            "impressions": int(row["impressions"]),
            "clicks": int(row["clicks"]),
            "spend": Decimal(str(row["spend"])),
            "orders": int(row["orders"]),
            "sales": Decimal(str(row["sales"])),
            "calculation_reasons": metric_calculation_reasons(
                impressions=int(row["impressions"]),
                clicks=int(row["clicks"]),
                spend=Decimal(str(row["spend"])),
                orders=int(row["orders"]),
                sales=Decimal(str(row["sales"])),
            ),
            "source_batch": batch,
        }
        if metric is None:
            new_metrics.append(
                SearchTermDailyMetric(
                    profile=profile,
                    campaign=campaign,
                    ad_group=ad_group,
                    search_term=search_term,
                    report_date=key[3],
                    targeting_expression_hash=expression_hash,
                    targeting_expression_snapshot=expression,
                    **defaults,
                )
            )
        else:
            previous_by_key[key] = {
                **_base_metric_values(metric),
                "targeting_expression_snapshot": (
                    metric.targeting_expression_snapshot
                ),
            }
            metric.targeting_expression_snapshot = expression
            for field, value in defaults.items():
                setattr(metric, field, value)
            changed_metrics.append(metric)
    if new_metrics:
        SearchTermDailyMetric.objects.bulk_create(new_metrics)
    if changed_metrics:
        SearchTermDailyMetric.objects.bulk_update(
            changed_metrics,
            [
                "targeting_expression_snapshot",
                "currency_code",
                "impressions",
                "clicks",
                "spend",
                "orders",
                "sales",
                "calculation_reasons",
                "source_batch",
                "updated_at",
            ],
        )
    published = [
        metric
        for metric in SearchTermDailyMetric.objects.filter(
            profile=profile,
            report_date__in=dates,
            targeting_expression_hash__in=expression_hashes,
        )
        if (
            metric.campaign_id,
            metric.ad_group_id,
            metric.search_term_id,
            metric.report_date,
            metric.targeting_expression_hash,
        )
        in prepared_keys
    ]
    revisions = []
    for metric in published:
        key = (
            metric.campaign_id,
            metric.ad_group_id,
            metric.search_term_id,
            metric.report_date,
            metric.targeting_expression_hash,
        )
        revisions.append(
            SearchTermMetricRevision(
                metric=metric,
                source_batch=batch,
                previous_values=previous_by_key.get(key, {}),
                current_values={
                    **_base_metric_values(metric),
                    "targeting_expression_snapshot": (
                        metric.targeting_expression_snapshot
                    ),
                },
            )
        )
    SearchTermMetricRevision.objects.bulk_create(revisions)
    return published
