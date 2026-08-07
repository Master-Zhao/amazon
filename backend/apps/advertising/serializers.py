from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from integrations.advertising_data.remote_campaign_aggregates import (
    METRIC_FILTER_FIELDS,
    METRIC_FILTER_OPERATORS,
)


CAMPAIGN_ORDERING_FIELDS = (
    "name",
    "targetingType",
    "status",
    "biddingStrategy",
    "startDate",
    "endDate",
    "dailyBudget",
    "impressions",
    "spend",
    "clicks",
    "ctr",
    "totalCost",
    "orders",
    "cpc",
    "acos",
    "cvr",
)
CAMPAIGN_REMOTE_STATES = {
    "enabled",
    "paused",
    "archived",
    "applying",
    "nothing",
    "refuse",
    "ended",
    "unknown",
}


class CampaignListQuerySerializer(serializers.Serializer):
    startDate = serializers.DateField(required=False, source="start_date")
    endDate = serializers.DateField(required=False, source="end_date")
    enabled = serializers.BooleanField(
        required=False,
        allow_null=True,
        default=None,
    )
    status = serializers.CharField(required=False, allow_blank=True, source="statuses")
    targetingType = serializers.ChoiceField(
        choices=("AUTO", "MANUAL"),
        required=False,
        source="targeting_type",
    )
    search = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        trim_whitespace=True,
    )
    metricFilters = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        source="metric_filters",
    )
    ordering = serializers.ChoiceField(
        choices=tuple(
            [*CAMPAIGN_ORDERING_FIELDS]
            + [f"-{field}" for field in CAMPAIGN_ORDERING_FIELDS]
        ),
        required=False,
        default="-spend",
    )
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    pageSize = serializers.IntegerField(
        required=False,
        default=15,
        min_value=1,
        max_value=100,
        source="page_size",
    )
    includeSummary = serializers.BooleanField(
        required=False,
        default=True,
        source="include_summary",
    )

    def validate_status(self, value: str) -> tuple[str, ...]:
        statuses = tuple(
            dict.fromkeys(
                item.strip().lower() for item in value.split(",") if item.strip()
            )
        )
        invalid = sorted(set(statuses) - CAMPAIGN_REMOTE_STATES)
        if invalid:
            raise serializers.ValidationError(
                f"Unsupported status values: {', '.join(invalid)}"
            )
        return statuses

    def validate_metricFilters(self, value: str) -> tuple[dict[str, object], ...]:
        if not value.strip():
            return ()
        rules = []
        seen_fields = set()
        for encoded in value.split(";"):
            parts = [part.strip() for part in encoded.split(":")]
            if len(parts) not in {3, 4}:
                raise serializers.ValidationError(
                    "Each metric filter must use field:operator:value[:value2]."
                )
            field, operator = parts[0], parts[1]
            if field not in METRIC_FILTER_FIELDS:
                raise serializers.ValidationError(f"Unsupported metric field: {field}")
            if operator not in METRIC_FILTER_OPERATORS:
                raise serializers.ValidationError(
                    f"Unsupported metric operator: {operator}"
                )
            if field in seen_fields:
                raise serializers.ValidationError(
                    f"Only one filter is allowed for metric: {field}"
                )
            if operator == "between" and len(parts) != 4:
                raise serializers.ValidationError(
                    "The between operator requires two values."
                )
            if operator != "between" and len(parts) != 3:
                raise serializers.ValidationError(
                    f"The {operator} operator requires one value."
                )
            try:
                first = Decimal(parts[2])
                second = Decimal(parts[3]) if len(parts) == 4 else None
            except InvalidOperation as exc:
                raise serializers.ValidationError(
                    "Metric filter values must be decimal numbers."
                ) from exc
            if second is not None and first > second:
                raise serializers.ValidationError(
                    "The first between value cannot exceed the second value."
                )
            rule = {"field": field, "operator": operator, "value": first}
            if second is not None:
                rule["value2"] = second
            rules.append(rule)
            seen_fields.add(field)
        if len(rules) > 9:
            raise serializers.ValidationError("At most 9 metric filters are allowed.")
        return tuple(rules)

    def validate(self, attrs):
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        if bool(start) != bool(end):
            raise serializers.ValidationError(
                "startDate and endDate must be provided together."
            )
        if start and end:
            if start > end:
                raise serializers.ValidationError(
                    {"endDate": "Must be on or after startDate."}
                )
            if (end - start).days > 89:
                raise serializers.ValidationError(
                    "Date range cannot exceed 90 inclusive days."
                )
        return attrs


class CampaignDetailQuerySerializer(serializers.Serializer):
    startDate = serializers.DateField(required=False, source="start_date")
    endDate = serializers.DateField(required=False, source="end_date")

    def validate(self, attrs):
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        if bool(start) != bool(end):
            raise serializers.ValidationError(
                "startDate and endDate must be provided together."
            )
        if start and end:
            if start > end:
                raise serializers.ValidationError(
                    {"endDate": "Must be on or after startDate."}
                )
            if (end - start).days > 89:
                raise serializers.ValidationError(
                    "Date range cannot exceed 90 inclusive days."
                )
        return attrs


class CampaignEnabledUpdateSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        if bool(start) != bool(end):
            raise serializers.ValidationError(
                "startDate and endDate must be provided together."
            )
        if start and end:
            if start > end:
                raise serializers.ValidationError(
                    {"endDate": "Must be on or after startDate."}
                )
            if (end - start).days > 89:
                raise serializers.ValidationError(
                    "Date range cannot exceed 90 inclusive days."
                )
        return attrs


class CampaignCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, trim_whitespace=True)
    targeting_type = serializers.ChoiceField(choices=("AUTO", "MANUAL"))
    daily_budget = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    bidding_strategy = serializers.ChoiceField(
        choices=("up_and_down", "down_only", "fixed_bids"),
        default="up_and_down",
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True)
    enabled = serializers.BooleanField(default=True)

    def validate(self, attrs):
        start = attrs["start_date"]
        end = attrs.get("end_date")
        if end and start > end:
            raise serializers.ValidationError(
                {"endDate": "Must be on or after startDate."}
            )
        return attrs


class MoneySerializer(serializers.Serializer):
    amount = serializers.CharField()
    currency_code = serializers.CharField()


class CampaignOverviewMetricsSerializer(serializers.Serializer):
    impressions = serializers.IntegerField(allow_null=True)
    top_of_search_share = serializers.CharField(allow_null=True)
    spend = MoneySerializer(allow_null=True)
    sales = MoneySerializer(allow_null=True)
    clicks = serializers.IntegerField(allow_null=True)
    ctr = serializers.CharField(allow_null=True)
    total_cost = MoneySerializer(allow_null=True)
    orders = serializers.IntegerField(allow_null=True)
    cpc = MoneySerializer(allow_null=True)
    acos = serializers.CharField(allow_null=True)
    cvr = serializers.CharField(allow_null=True)


class CampaignOverviewItemSerializer(serializers.Serializer):
    campaign_key = serializers.CharField()
    name = serializers.CharField()
    campaign_code = serializers.CharField()
    enabled = serializers.BooleanField()
    targeting_type = serializers.CharField()
    status = serializers.CharField()
    bidding_strategy = serializers.CharField()
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(allow_null=True)
    daily_budget = MoneySerializer(allow_null=True)
    metrics = CampaignOverviewMetricsSerializer()
    metadata_matched = serializers.BooleanField()
    has_metrics = serializers.BooleanField()
    partial_fields = serializers.ListField(child=serializers.CharField())


class CampaignPaginationSerializer(serializers.Serializer):
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total = serializers.IntegerField()
    total_pages = serializers.IntegerField()


class CampaignOverviewMetaSerializer(serializers.Serializer):
    source = serializers.CharField()
    currency_code = serializers.CharField()
    timezone = serializers.CharField()
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(allow_null=True)
    data_through_date = serializers.DateField(allow_null=True)
    history_through_date = serializers.DateField(allow_null=True)
    realtime_through_date = serializers.DateField(allow_null=True)
    realtime_as_of = serializers.DateTimeField(allow_null=True)
    deduplication_version = serializers.CharField()
    field_mappings = serializers.DictField(child=serializers.CharField())
    total_cost_semantics = serializers.CharField()
    attribution_semantics = serializers.CharField()
    status_filter_semantics = serializers.CharField()


class CampaignTrendPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    metrics = CampaignOverviewMetricsSerializer()


class CampaignRiskLevelSerializer(serializers.Serializer):
    level = serializers.CharField()
    count = serializers.IntegerField()


class CampaignDashboardSerializer(serializers.Serializer):
    trend = CampaignTrendPointSerializer(many=True)
    risk_levels = CampaignRiskLevelSerializer(many=True)
    evaluated_campaigns = serializers.IntegerField()
    target_acos = serializers.CharField(allow_null=True)
    unavailable_rule_codes = serializers.ListField(child=serializers.CharField())
    risk_semantics = serializers.CharField()


class CampaignOverviewResponseSerializer(serializers.Serializer):
    items = CampaignOverviewItemSerializer(many=True)
    summary = CampaignOverviewMetricsSerializer(allow_null=True)
    dashboard = CampaignDashboardSerializer()
    pagination = CampaignPaginationSerializer()
    meta = CampaignOverviewMetaSerializer()


class CampaignDetailResponseSerializer(serializers.Serializer):
    item = CampaignOverviewItemSerializer()
    trend = CampaignTrendPointSerializer(many=True)
    meta = CampaignOverviewMetaSerializer()


class CampaignEnabledUpdateResponseSerializer(serializers.Serializer):
    item = CampaignOverviewItemSerializer()


class CampaignCreateResponseSerializer(serializers.Serializer):
    item = CampaignOverviewItemSerializer()


class CampaignRowSerializer(serializers.Serializer):
    id = serializers.CharField()
    external_campaign_id = serializers.CharField()
    name = serializers.CharField()
    ad_product_type = serializers.CharField()
    state = serializers.CharField()
    daily_budget = serializers.CharField(allow_null=True)
    currency_code = serializers.CharField()
    source_batch_id = serializers.CharField(allow_null=True)


class TargetingRowSerializer(serializers.Serializer):
    id = serializers.CharField()
    target_type = serializers.CharField()
    external_target_id = serializers.CharField()
    target_text = serializers.CharField()
    match_type = serializers.CharField(allow_null=True)
    state = serializers.CharField()
    bid = serializers.CharField(allow_null=True)
    campaign_id = serializers.CharField()
    campaign_name = serializers.CharField()
    ad_group_id = serializers.CharField()
    ad_group_name = serializers.CharField()
    source_batch_id = serializers.CharField(allow_null=True)


class SearchTermRowSerializer(serializers.Serializer):
    id = serializers.CharField()
    display_text = serializers.CharField()
    normalized_text = serializers.CharField()
    text_hash = serializers.CharField()
