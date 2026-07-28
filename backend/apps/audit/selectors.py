from apps.audit.models import AuditLog
from apps.permissions.services import require_feature_permission, require_membership
from apps.tenants.models import MembershipRole


def audit_logs_for_tenant(*, user, tenant_id, event: str | None = None):
    membership = require_membership(user=user, tenant_id=tenant_id)
    require_feature_permission(membership, "audit.view")
    logs = AuditLog.objects.filter(tenant=membership.tenant).select_related("actor")
    if membership.membership_role not in {
        MembershipRole.OWNER,
        MembershipRole.ADMIN,
    }:
        logs = logs.filter(actor=user)
    if event:
        logs = logs.filter(event=event)
    return logs.order_by("-created_at")[:200]
