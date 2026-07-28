from django.db.models import QuerySet

from apps.tenants.models import Tenant, TenantMembership


def memberships_for_user(user) -> QuerySet[TenantMembership]:
    return (
        TenantMembership.objects.filter(user=user, is_active=True, tenant__is_active=True)
        .select_related("tenant")
        .order_by("tenant__name", "tenant_id")
    )


def tenants_for_user(user) -> QuerySet[Tenant]:
    return Tenant.objects.filter(
        memberships__user=user,
        memberships__is_active=True,
        is_active=True,
    ).distinct()
