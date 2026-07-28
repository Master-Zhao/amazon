from django.db.models import Q

from apps.permissions.models import Permission, Role
from apps.permissions.services import require_tenant_management


def role_options(*, user, tenant_id) -> list[dict]:
    membership = require_tenant_management(user=user, tenant_id=tenant_id)
    roles = (
        Role.objects.filter(
            Q(tenant=membership.tenant) | Q(tenant__isnull=True),
            is_active=True,
        )
        .prefetch_related("role_permissions__permission")
        .order_by("-is_system", "name")
    )
    return [
        {
            "id": str(role.pk),
            "name": role.name,
            "code": role.code,
            "is_system": role.is_system,
            "permission_codes": sorted(
                item.permission.code for item in role.role_permissions.all()
            ),
        }
        for role in roles
    ]


def permission_options(*, user, tenant_id) -> list[dict]:
    require_tenant_management(user=user, tenant_id=tenant_id)
    return [
        {"id": str(item.pk), "code": item.code, "name": item.name}
        for item in Permission.objects.order_by("code")
    ]
