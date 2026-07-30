from rest_framework import serializers


class FormulaValueSerializer(serializers.Serializer):
    value = serializers.CharField(allow_null=True)
    reason = serializers.CharField(allow_null=True)


class AnomalySerializer(serializers.Serializer):
    id = serializers.CharField()
    rule_code = serializers.CharField()
    rule_version = serializers.IntegerField()
    status = serializers.CharField()
    risk_level = serializers.CharField(allow_null=True, allow_blank=True)
    observed_value = serializers.CharField(allow_null=True)
    threshold_value = serializers.CharField(allow_null=True)
    reason_code = serializers.CharField(allow_blank=True)
    explanation = serializers.CharField()


class DashboardRowSerializer(serializers.Serializer):
    marketplace_code = serializers.CharField()
    marketplace_name = serializers.CharField()
    currency_code = serializers.CharField()
    campaign_count = serializers.IntegerField()
    impressions = serializers.IntegerField()
    clicks = serializers.IntegerField()
    spend = serializers.CharField()
    orders = serializers.IntegerField()
    sales = serializers.CharField()
    ctr = FormulaValueSerializer()
    cpc = FormulaValueSerializer()
    cvr = FormulaValueSerializer()
    acos = FormulaValueSerializer()
    roas = FormulaValueSerializer()
    anomaly_count = serializers.IntegerField()
    authoritative_grain = serializers.CharField()


class CampaignMetricRowSerializer(serializers.Serializer):
    id = serializers.CharField()
    campaign_id = serializers.CharField()
    external_campaign_id = serializers.CharField()
    campaign_name = serializers.CharField()
    report_date = serializers.DateField()
    currency_code = serializers.CharField()
    impressions = serializers.IntegerField()
    clicks = serializers.IntegerField()
    spend = serializers.CharField()
    orders = serializers.IntegerField()
    sales = serializers.CharField()
    calculation_reasons = serializers.DictField()
    daily_budget_snapshot = serializers.CharField(allow_null=True)
    snapshot_hour_local = serializers.IntegerField(allow_null=True)
    state_snapshot = serializers.CharField()
    target_acos = serializers.CharField(allow_null=True)
    ctr = FormulaValueSerializer()
    cpc = FormulaValueSerializer()
    cvr = FormulaValueSerializer()
    acos = FormulaValueSerializer()
    roas = FormulaValueSerializer()
    source_batch_id = serializers.CharField()
    anomalies = AnomalySerializer(many=True)


class CampaignDetailSerializer(serializers.Serializer):
    campaign_id = serializers.CharField()
    external_campaign_id = serializers.CharField()
    campaign_name = serializers.CharField()
    state = serializers.CharField()
    target_acos = serializers.CharField(allow_null=True)
    metrics = CampaignMetricRowSerializer(many=True)


class CampaignTargetAcosSerializer(serializers.Serializer):
    campaign_id = serializers.CharField()
    campaign_name = serializers.CharField()
    target_acos = serializers.CharField(allow_null=True)
    effective_target_acos = serializers.CharField(allow_null=True)


class AnomalyRuleVersionSerializer(serializers.Serializer):
    id = serializers.CharField()
    code = serializers.CharField()
    version = serializers.IntegerField()
    scope_key = serializers.CharField()
    configuration = serializers.DictField()
    created_at = serializers.DateTimeField()


class AnalyticsConfigurationSerializer(serializers.Serializer):
    tenant_target_acos = serializers.CharField(allow_null=True)
    profile_target_acos = serializers.CharField(allow_null=True)
    campaigns = CampaignTargetAcosSerializer(many=True)
    rules = AnomalyRuleVersionSerializer(many=True)


class TargetAcosUpdateSerializer(serializers.Serializer):
    scope_type = serializers.ChoiceField(
        choices=["TENANT", "PROFILE", "CAMPAIGN"]
    )
    campaign_id = serializers.CharField(required=False, allow_null=True)
    target_acos = serializers.DecimalField(
        max_digits=8,
        decimal_places=4,
        allow_null=True,
    )

    def validate(self, attrs):
        if attrs["scope_type"] == "CAMPAIGN" and not attrs.get("campaign_id"):
            raise serializers.ValidationError(
                {"campaign_id": ["Required for CAMPAIGN scope."]}
            )
        return attrs


class AnomalyRuleCreateSerializer(serializers.Serializer):
    code = serializers.CharField()
    scope_type = serializers.ChoiceField(
        choices=["TENANT", "PROFILE", "CAMPAIGN"]
    )
    campaign_id = serializers.CharField(required=False, allow_null=True)
    configuration = serializers.DictField()

    def validate(self, attrs):
        if attrs["scope_type"] == "CAMPAIGN" and not attrs.get("campaign_id"):
            raise serializers.ValidationError(
                {"campaign_id": ["Required for CAMPAIGN scope."]}
            )
        return attrs


class TargetingMetricRowSerializer(serializers.Serializer):
    id = serializers.CharField()
    campaign_id = serializers.CharField()
    campaign_name = serializers.CharField()
    ad_group_id = serializers.CharField()
    ad_group_name = serializers.CharField()
    target_type = serializers.CharField()
    target_id = serializers.CharField()
    target_text = serializers.CharField()
    match_type = serializers.CharField(allow_null=True)
    report_date = serializers.DateField()
    currency_code = serializers.CharField()
    impressions = serializers.IntegerField()
    clicks = serializers.IntegerField()
    spend = serializers.CharField()
    orders = serializers.IntegerField()
    sales = serializers.CharField()
    calculation_reasons = serializers.DictField()
    bid_snapshot = serializers.CharField(allow_null=True)
    state_snapshot = serializers.CharField()
    ctr = FormulaValueSerializer()
    cpc = FormulaValueSerializer()
    cvr = FormulaValueSerializer()
    acos = FormulaValueSerializer()
    roas = FormulaValueSerializer()
    source_batch_id = serializers.CharField()


class SearchTermMetricRowSerializer(serializers.Serializer):
    id = serializers.CharField()
    campaign_id = serializers.CharField()
    campaign_name = serializers.CharField()
    ad_group_id = serializers.CharField()
    ad_group_name = serializers.CharField()
    search_term_id = serializers.CharField()
    search_term = serializers.CharField()
    targeting_expression = serializers.CharField()
    report_date = serializers.DateField()
    currency_code = serializers.CharField()
    impressions = serializers.IntegerField()
    clicks = serializers.IntegerField()
    spend = serializers.CharField()
    orders = serializers.IntegerField()
    sales = serializers.CharField()
    calculation_reasons = serializers.DictField()
    ctr = FormulaValueSerializer()
    cpc = FormulaValueSerializer()
    cvr = FormulaValueSerializer()
    acos = FormulaValueSerializer()
    roas = FormulaValueSerializer()
    source_batch_id = serializers.CharField()


class RemoteCampaignMetricRowSerializer(serializers.Serializer):
    id = serializers.CharField()
    external_campaign_id = serializers.CharField()
    campaign_name = serializers.CharField()
    report_date = serializers.DateField()
    currency_code = serializers.CharField()
    impressions = serializers.IntegerField()
    clicks = serializers.IntegerField()
    spend = serializers.CharField()
    orders = serializers.IntegerField()
    sales = serializers.CharField()
    daily_budget = serializers.CharField(allow_null=True)
    state = serializers.CharField()
    ctr = FormulaValueSerializer()
    cpc = FormulaValueSerializer()
    cvr = FormulaValueSerializer()
    acos = FormulaValueSerializer()
    roas = FormulaValueSerializer()
    scm_matched = serializers.BooleanField()
    source_system = serializers.CharField()
