from django.db import transaction
from rest_framework.exceptions import NotFound

from apps.audit.services import append_audit_log
from apps.permissions.models import Role, UserRole
from apps.permissions.services import require_tenant_management
from apps.tenants.models import Team, TeamMember, TenantMembership


@transaction.atomic
def create_team(*, request, tenant_id, name: str) -> Team:
    manager = require_tenant_management(user=request.user, tenant_id=tenant_id)
    team = Team.objects.create(tenant=manager.tenant, name=name)
    append_audit_log(
        request=request,
        tenant=manager.tenant,
        actor=request.user,
        event="team.created",
        object_type="Team",
        object_id=team.pk,
        after_data={"name": team.name},
    )
    return team


@transaction.atomic
def add_team_member(*, request, tenant_id, team_id, membership_id) -> TeamMember:
    manager = require_tenant_management(user=request.user, tenant_id=tenant_id)
    team = Team.objects.filter(
        pk=team_id,
        tenant=manager.tenant,
        is_active=True,
    ).first()
    membership = TenantMembership.objects.filter(
        pk=membership_id,
        tenant=manager.tenant,
        is_active=True,
    ).first()
    if team is None or membership is None:
        raise NotFound("Team 或 Membership 不存在或不在当前卖家空间")
    item, created = TeamMember.objects.get_or_create(
        team=team,
        membership=membership,
    )
    if created:
        append_audit_log(
            request=request,
            tenant=manager.tenant,
            actor=request.user,
            event="team.member_added",
            object_type="Team",
            object_id=team.pk,
            after_data={"membership_id": str(membership.pk)},
        )
    return item


@transaction.atomic
def assign_role(*, request, tenant_id, membership_id, role_id) -> UserRole:
    manager = require_tenant_management(user=request.user, tenant_id=tenant_id)
    membership = TenantMembership.objects.filter(
        pk=membership_id,
        tenant=manager.tenant,
        is_active=True,
    ).first()
    role = Role.objects.filter(
        pk=role_id,
        is_active=True,
    ).first()
    if (
        membership is None
        or role is None
        or (role.tenant_id is not None and role.tenant_id != manager.tenant_id)
    ):
        raise NotFound("Membership 或 Role 不存在或不在当前卖家空间")
    item, created = UserRole.objects.get_or_create(
        membership=membership,
        role=role,
    )
    if created:
        append_audit_log(
            request=request,
            tenant=manager.tenant,
            actor=request.user,
            event="role.assigned",
            object_type="TenantMembership",
            object_id=membership.pk,
            after_data={"role_id": str(role.pk), "role_code": role.code},
        )
    return item
