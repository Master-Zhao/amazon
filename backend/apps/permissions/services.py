from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.permissions.models import (
    PROFILE_LEVEL_RANK,
    Permission,
    ProfileAccessLevel,
    Role,
    RolePermission,
    TeamProfileAccess,
    TeamStoreAccess,
    UserProfileAccess,
    UserRole,
    UserStoreAccess,
)
from apps.stores.models import AdvertisingProfile, AmazonStore
from apps.tenants.models import MembershipRole, TeamMember, Tenant, TenantMembership

PERMISSION_CATALOG = {
    "context.view": "查看卖家空间上下文",
    "members.manage": "管理成员",
    "roles.manage": "管理角色",
    "stores.manage": "管理店铺",
    "profiles.manage": "管理广告 Profile",
    "reports.view": "查看报表",
    "reports.import": "导入报表",
    "analytics.view": "查看广告分析",
    "analysis.run": "运行智能分析",
    "recommendations.view": "查看建议",
    "actions.submit": "提交动作方案",
    "actions.approve": "审批动作方案",
    "actions.execute": "回填人工执行",
    "audit.view": "查看审计日志",
    "knowledge.view": "查看知识中心",
}


@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    membership: TenantMembership
    permission_codes: frozenset[str]
    profile_level: str | None = None


def _active_membership(*, user, tenant_id) -> TenantMembership:
    try:
        return TenantMembership.objects.select_related("tenant").get(
            tenant_id=tenant_id,
            user=user,
            is_active=True,
            tenant__is_active=True,
        )
    except (TenantMembership.DoesNotExist, ValueError, TypeError) as exc:
        raise NotFound("资源不存在或不在当前卖家空间范围") from exc


def permission_codes_for(*, user, tenant: Tenant) -> frozenset[str]:
    membership = _active_membership(user=user, tenant_id=tenant.pk)
    if membership.role in {MembershipRole.OWNER, MembershipRole.ADMIN}:
        return frozenset(Permission.objects.values_list("code", flat=True))
    return frozenset(
        Permission.objects.filter(
            roles__userrole__tenant=tenant,
            roles__userrole__user=user,
        ).values_list("code", flat=True)
    )


def accessible_store_ids(*, user, tenant: Tenant) -> set:
    membership = _active_membership(user=user, tenant_id=tenant.pk)
    if membership.role in {MembershipRole.OWNER, MembershipRole.ADMIN}:
        return set(
            AmazonStore.objects.filter(tenant=tenant, is_active=True).values_list(
                "id", flat=True
            )
        )
    team_ids = TeamMember.objects.filter(
        membership=membership,
        team__is_active=True,
    ).values_list("team_id", flat=True)
    direct = UserStoreAccess.objects.filter(
        user=user, store__tenant=tenant, store__is_active=True
    ).values_list("store_id", flat=True)
    team = TeamStoreAccess.objects.filter(
        team_id__in=team_ids, store__tenant=tenant, store__is_active=True
    ).values_list("store_id", flat=True)
    return set(direct).union(team)


def effective_profile_level(*, user, profile: AdvertisingProfile) -> str | None:
    tenant = profile.store_marketplace.store.tenant
    membership = _active_membership(user=user, tenant_id=tenant.pk)
    if membership.role in {MembershipRole.OWNER, MembershipRole.ADMIN}:
        return ProfileAccessLevel.MANAGE
    if profile.store_marketplace.store_id not in accessible_store_ids(
        user=user, tenant=tenant
    ):
        return None
    levels = list(
        UserProfileAccess.objects.filter(user=user, profile=profile).values_list(
            "level", flat=True
        )
    )
    team_ids = TeamMember.objects.filter(
        membership=membership, team__is_active=True
    ).values_list("team_id", flat=True)
    levels.extend(
        TeamProfileAccess.objects.filter(
            team_id__in=team_ids, profile=profile
        ).values_list("level", flat=True)
    )
    if not levels:
        return None
    return max(levels, key=lambda level: PROFILE_LEVEL_RANK[level])


def authorize(
    *,
    user,
    tenant_id,
    permission_code: str | None = None,
    store: AmazonStore | None = None,
    profile: AdvertisingProfile | None = None,
    minimum_profile_level: str = ProfileAccessLevel.VIEW,
) -> AuthorizationContext:
    membership = _active_membership(user=user, tenant_id=tenant_id)
    tenant = membership.tenant
    codes = permission_codes_for(user=user, tenant=tenant)
    if permission_code and permission_code not in codes:
        raise PermissionDenied("当前卖家空间内缺少功能权限")
    if store is not None:
        if store.tenant_id != tenant.pk:
            raise NotFound("资源不存在或不在当前卖家空间范围")
        if store.pk not in accessible_store_ids(user=user, tenant=tenant):
            raise NotFound("资源不存在或不在当前卖家空间范围")
    level = None
    if profile is not None:
        if profile.store_marketplace.store.tenant_id != tenant.pk:
            raise NotFound("资源不存在或不在当前卖家空间范围")
        level = effective_profile_level(user=user, profile=profile)
        if level is None:
            raise NotFound("资源不存在或不在当前卖家空间范围")
        if PROFILE_LEVEL_RANK[level] < PROFILE_LEVEL_RANK[minimum_profile_level]:
            raise PermissionDenied("当前广告 Profile 操作等级不足")
    return AuthorizationContext(membership, codes, level)


@transaction.atomic
def seed_permission_catalog() -> None:
    for code, name in PERMISSION_CATALOG.items():
        Permission.objects.update_or_create(code=code, defaults={"name": name})


@transaction.atomic
def create_role(
    *, actor, tenant: Tenant, code: str, name: str, permission_codes: list[str]
) -> Role:
    authorize(
        user=actor, tenant_id=tenant.pk, permission_code="roles.manage"
    )
    permissions = list(Permission.objects.filter(code__in=set(permission_codes)))
    if len(permissions) != len(set(permission_codes)):
        raise ValueError("Custom roles can only use existing permission codes")
    role = Role.objects.create(
        tenant=tenant,
        code=code.strip().lower(),
        name=name.strip(),
        is_system=False,
    )
    RolePermission.objects.bulk_create(
        [RolePermission(role=role, permission=permission) for permission in permissions]
    )
    return role


@transaction.atomic
def assign_role(*, actor, tenant: Tenant, role: Role, user_id) -> UserRole:
    authorize(
        user=actor, tenant_id=tenant.pk, permission_code="roles.manage"
    )
    if role.tenant_id not in {None, tenant.pk}:
        raise NotFound("角色不存在或不属于当前卖家空间")
    user_model = get_user_model()
    try:
        target = user_model.objects.get(pk=user_id)
        TenantMembership.objects.get(tenant=tenant, user=target, is_active=True)
    except (user_model.DoesNotExist, TenantMembership.DoesNotExist) as exc:
        raise NotFound("成员不存在") from exc
    assignment, _ = UserRole.objects.get_or_create(
        tenant=tenant, user=target, role=role
    )
    return assignment


def _tenant_member_user(*, tenant: Tenant, user_id):
    user_model = get_user_model()
    try:
        target = user_model.objects.get(pk=user_id)
        TenantMembership.objects.get(tenant=tenant, user=target, is_active=True)
    except (user_model.DoesNotExist, TenantMembership.DoesNotExist) as exc:
        raise NotFound("成员不存在") from exc
    return target


@transaction.atomic
def grant_user_store_access(
    *, actor, tenant: Tenant, store: AmazonStore, user_id
) -> UserStoreAccess:
    authorize(
        user=actor,
        tenant_id=tenant.pk,
        permission_code="stores.manage",
        store=store,
    )
    target = _tenant_member_user(tenant=tenant, user_id=user_id)
    grant, _ = UserStoreAccess.objects.get_or_create(store=store, user=target)
    return grant


@transaction.atomic
def grant_user_profile_access(
    *,
    actor,
    tenant: Tenant,
    profile: AdvertisingProfile,
    user_id,
    level: str,
) -> UserProfileAccess:
    if level not in ProfileAccessLevel.values:
        raise ValueError("Unsupported profile access level")
    authorize(
        user=actor,
        tenant_id=tenant.pk,
        permission_code="profiles.manage",
        profile=profile,
        minimum_profile_level=ProfileAccessLevel.MANAGE,
    )
    target = _tenant_member_user(tenant=tenant, user_id=user_id)
    grant, _ = UserProfileAccess.objects.update_or_create(
        profile=profile, user=target, defaults={"level": level}
    )
    UserStoreAccess.objects.get_or_create(
        store=profile.store_marketplace.store, user=target
    )
    return grant
