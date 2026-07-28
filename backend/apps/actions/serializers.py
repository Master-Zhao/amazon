from rest_framework import serializers


class PreviewCreateSerializer(serializers.Serializer):
    tenantId = serializers.UUIDField()
    profileId = serializers.UUIDField()
    recommendationIds = serializers.ListField(child=serializers.UUIDField(), min_length=1)


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["APPROVED", "REJECTED", "RETURNED"])
    comment = serializers.CharField(max_length=500, required=False, default="")


class ExecutionRecordSerializer(serializers.Serializer):
    result = serializers.ChoiceField(choices=["SUCCEEDED", "FAILED", "SKIPPED"])
    actualValue = serializers.JSONField(required=False, default=dict)
    executedAt = serializers.DateTimeField()
    note = serializers.CharField(max_length=500, required=False, default="")

