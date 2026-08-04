from rest_framework import serializers


CAMPAIGN_ORDERING_FIELDS = (
    "name",
    "targetingType",
    "status",
    "biddingStrategy",
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
    enabled = serializers.BooleanField(required=False, default=True)
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


class MoneySerializer(serializers.Serializer):
    amount = serializers.CharField()
    currency_code = serializers.CharField()


class CampaignOverviewMetricsSerializer(serializers.Serializer):
    impressions = serializers.IntegerField()
    top_of_search_share = serializers.CharField(allow_null=True)
    spend = MoneySerializer()
    sales = MoneySerializer()
    clicks = serializers.IntegerField()
    ctr = serializers.CharField(allow_null=True)
    total_cost = MoneySerializer()
    orders = serializers.IntegerField()
    cpc = MoneySerializer(allow_null=True)
    acos = serializers.CharField(allow_null=True)
    cvr = serializers.CharField(allow_null=True)


class CampaignOverviewItemSerializer(serializers.Serializer):
    campaign_key = serializers.CharField()
    name = serializers.CharField()
    reference_code = serializers.CharField()
    enabled = serializers.BooleanField()
    targeting_type = serializers.CharField()
    status = serializers.CharField()
    bidding_strategy = serializers.CharField()
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(allow_null=True)
    daily_budget = MoneySerializer(allow_null=True)
    metrics = CampaignOverviewMetricsSerializer()
    metadata_matched = serializers.BooleanField()
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
