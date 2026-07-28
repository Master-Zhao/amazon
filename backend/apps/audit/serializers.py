from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", allow_null=True)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "event",
            "object_type",
            "object_id",
            "request_id",
            "task_id",
            "actor_email",
            "before_data",
            "after_data",
            "metadata",
            "created_at",
        )
