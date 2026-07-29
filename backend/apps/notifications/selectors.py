from apps.notifications.models import Notification
from apps.permissions.services import require_membership
from apps.tenants.models import MembershipRole


def notifications_for_user(*, user, tenant_id=None):
    if tenant_id:
        membership = require_membership(user=user, tenant_id=tenant_id)
        return Notification.objects.filter(
            recipient=user, tenant=membership.tenant,
        ).select_related("tenant").order_by("-created_at")[:50]
    return Notification.objects.filter(
        recipient=user,
    ).select_related("tenant").order_by("-created_at")[:50]