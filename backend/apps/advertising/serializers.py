from rest_framework import serializers


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
