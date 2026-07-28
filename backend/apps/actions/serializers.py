from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.actions.models import (
    ActionPreview,
    ActionPreviewVersion,
    ApprovalDecision,
    ApprovalRecord,
    ExecutionOutcome,
    ExecutionRecord,
)


class ActionPreviewVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionPreviewVersion
        fields = (
            "id",
            "version_number",
            "action_payload",
            "object_state_version",
            "created_at",
        )


class ApprovalRecordSerializer(serializers.ModelSerializer):
    decided_by_email = serializers.EmailField(source="decided_by.email")

    class Meta:
        model = ApprovalRecord
        fields = (
            "id",
            "decision",
            "comment",
            "decided_by_email",
            "created_at",
        )


class ExecutionRecordSerializer(serializers.ModelSerializer):
    recorded_by_email = serializers.EmailField(source="recorded_by.email")

    class Meta:
        model = ExecutionRecord
        fields = (
            "id",
            "outcome",
            "actual_value",
            "executed_at",
            "note",
            "evidence_metadata",
            "recorded_by_email",
            "created_at",
        )


class ActionPreviewSerializer(serializers.ModelSerializer):
    campaign_name = serializers.CharField(
        source="recommendation_revision.recommendation.campaign.name"
    )
    action_type = serializers.CharField(
        source="recommendation_revision.action_type"
    )
    current_version = serializers.SerializerMethodField()
    approvals = ApprovalRecordSerializer(
        source="approval_records",
        many=True,
        read_only=True,
    )
    executions = ExecutionRecordSerializer(
        source="execution_records",
        many=True,
        read_only=True,
    )

    @extend_schema_field(ActionPreviewVersionSerializer)
    def get_current_version(self, instance):
        version = next(
            (
                item
                for item in instance.versions.all()
                if item.version_number == instance.current_version_number
            ),
            None,
        )
        return (
            ActionPreviewVersionSerializer(version).data
            if version is not None
            else None
        )

    class Meta:
        model = ActionPreview
        fields = (
            "id",
            "status",
            "campaign_name",
            "action_type",
            "current_version_number",
            "current_version",
            "approvals",
            "executions",
            "created_at",
            "updated_at",
        )


class ApprovalDecisionRequestSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=ApprovalDecision.choices)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    idempotency_key = serializers.CharField(max_length=128)


class ManualExecutionRequestSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=ExecutionOutcome.choices)
    actual_value = serializers.JSONField()
    executed_at = serializers.DateTimeField()
    note = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    evidence_metadata = serializers.JSONField(required=False)
    idempotency_key = serializers.CharField(max_length=128)
