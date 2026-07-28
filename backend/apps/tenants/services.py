from django.db import transaction

from apps.tenants.models import MembershipRole, Tenant, TenantMembership, TenantType


@transaction.atomic
def create_tenant(*, owner, name: str, tenant_type: str) -> Tenant:
    if tenant_type not in TenantType.values:
        raise ValueError("Unsupported tenant type")
    tenant = Tenant.objects.create(name=name.strip(), tenant_type=tenant_type)
    TenantMembership.objects.create(
        tenant=tenant, user=owner, role=MembershipRole.OWNER
    )
    return tenant

