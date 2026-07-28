from rest_framework import serializers


class PreviewCreateSerializer(serializers.Serializer):
    tenant_id = serializers.UUIDField()
    profile_id = serializers.UUIDField()
    recommendation_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1
    )


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["APPROVED", "REJECTED", "RETURNED"])
    comment = serializers.CharField(max_length=500, required=False, default="")


class ExecutionRecordSerializer(serializers.Serializer):
    result = serializers.ChoiceField(choices=["SUCCEEDED", "FAILED", "SKIPPED"])
    actual_value = serializers.JSONField(required=False, default=dict)
    executed_at = serializers.DateTimeField()
    note = serializers.CharField(max_length=500, required=False, default="")
    evidence = serializers.FileField(required=False, allow_empty_file=False, write_only=True)
