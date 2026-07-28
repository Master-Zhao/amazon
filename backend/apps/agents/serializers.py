from rest_framework import serializers

from apps.agents.models import AgentRun


class AgentRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentRun
        fields = (
            "id",
            "agent_code",
            "status",
            "schema_version",
            "celery_task_id",
            "output_result",
            "error_code",
            "error_message",
            "created_at",
            "started_at",
            "finished_at",
        )
