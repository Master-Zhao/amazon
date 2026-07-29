from django.utils import timezone

from apps.notifications.models import Notification


def list_notifications(*, user, tenant_id=None):
    qs = Notification.objects.filter(recipient=user).select_related("tenant")
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    return qs.order_by("-created_at")[:50]


def unread_count(*, user):
    return Notification.objects.filter(recipient=user, is_read=False).count()


def mark_read(*, user, notification_id) -> Notification:
    notification = Notification.objects.filter(
        pk=notification_id, recipient=user,
    ).first()
    if notification is None:
        from rest_framework.exceptions import NotFound
        raise NotFound("通知不存在或不在当前数据范围")
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])
    return notification


def mark_all_read(*, user) -> int:
    now = timezone.now()
    return Notification.objects.filter(
        recipient=user, is_read=False,
    ).update(is_read=True, read_at=now)