from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.recommendations.models import Recommendation, RecommendationRevision


class RecommendationRevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendationRevision
        fields = (
            "id",
            "revision_number",
            "schema_version",
            "action_type",
            "object_type",
            "object_id",
            "before_value",
            "after_value",
            "reason",
            "evidence",
            "risk_level",
            "created_at",
        )


class RecommendationSerializer(serializers.ModelSerializer):
    campaign_name = serializers.CharField(source="campaign.name")
    external_campaign_id = serializers.CharField(
        source="campaign.external_campaign_id"
    )
    current_revision = serializers.SerializerMethodField()

    @extend_schema_field(RecommendationRevisionSerializer)
    def get_current_revision(self, instance):
        revision = next(
            (
                item
                for item in instance.revisions.all()
                if item.revision_number == instance.current_revision_number
            ),
            None,
        )
        return (
            RecommendationRevisionSerializer(revision).data
            if revision is not None
            else None
        )

    class Meta:
        model = Recommendation
        fields = (
            "id",
            "status",
            "action_type",
            "campaign_name",
            "external_campaign_id",
            "agent_run_id",
            "current_revision_number",
            "current_revision",
            "created_at",
        )


class DismissRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class ReviseRequestSerializer(serializers.Serializer):
    afterValue = serializers.JSONField()
    reason = serializers.CharField(max_length=1000)
    evidence = serializers.JSONField()
    riskLevel = serializers.ChoiceField(choices=["LOW", "MEDIUM", "HIGH"])
