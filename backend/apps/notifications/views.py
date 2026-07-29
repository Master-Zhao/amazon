from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import api_response
from apps.notifications.selectors import notifications_for_user
from apps.notifications.serializers import (
    MarkedCountSerializer,
    NotificationSerializer,
    UnreadCountSerializer,
)
from apps.notifications.services import list_notifications, mark_all_read, mark_read, unread_count


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List notifications for current user",
        parameters=[
            OpenApiParameter("tenant_id", str, required=False),
        ],
        responses={200: NotificationSerializer(many=True)},
        tags=["notifications"],
    )
    def get(self, request):
        tenant_id = request.query_params.get("tenant_id")
        notifications = notifications_for_user(
            user=request.user,
            tenant_id=tenant_id,
        )
        return api_response(
            request,
            data=NotificationSerializer(notifications, many=True).data,
        )


class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get unread notification count",
        responses={200: UnreadCountSerializer},
        tags=["notifications"],
    )
    def get(self, request):
        count = unread_count(user=request.user)
        return api_response(
            request,
            data={"unread_count": count},
        )


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Mark a notification as read",
        request=None,
        responses={200: NotificationSerializer},
        tags=["notifications"],
    )
    def post(self, request, pk):
        notification = mark_read(user=request.user, notification_id=pk)
        return api_response(
            request,
            data=NotificationSerializer(notification).data,
        )


class MarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Mark all notifications as read",
        request=None,
        responses={200: MarkedCountSerializer},
        tags=["notifications"],
    )
    def post(self, request):
        count = mark_all_read(user=request.user)
        return api_response(
            request,
            data={"marked_count": count},
        )
