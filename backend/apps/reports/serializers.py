from rest_framework import serializers


class ReportUploadSerializer(serializers.Serializer):
    tenantId = serializers.UUIDField()
    profileId = serializers.UUIDField()
    reportType = serializers.ChoiceField(
        choices=["CAMPAIGN", "TARGETING", "SEARCH_TERM"]
    )
    file = serializers.FileField()


class TaskDataSerializer(serializers.Serializer):
    taskId = serializers.CharField()
    status = serializers.CharField()
    isDuplicate = serializers.BooleanField()
    taskUrl = serializers.CharField()


class TaskResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    data = TaskDataSerializer()
    requestId = serializers.CharField()
