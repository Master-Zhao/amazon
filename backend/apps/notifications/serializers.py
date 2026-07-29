from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "notification_type",
            "title",
            "content",
            "target_route",
            "is_read",
            "read_at",
            "created_at",
        )


class UnreadCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()


class MarkedCountSerializer(serializers.Serializer):
    marked_count = serializers.IntegerField()
