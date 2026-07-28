from rest_framework import serializers


class AnalysisCreateSerializer(serializers.Serializer):
    tenantId = serializers.UUIDField()
    profileId = serializers.UUIDField()

