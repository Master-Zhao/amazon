from rest_framework import serializers


class AnalysisCreateSerializer(serializers.Serializer):
    tenant_id = serializers.UUIDField()
    profile_id = serializers.UUIDField()
