from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Max, Q, QuerySet
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.serializers import ValidationError

from apps.audit.services import append_audit_log
from apps.permissions.models import (
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
from apps.tenants.models import MembershipRole, Team, TeamMember, TenantMembership


@dataclass(frozen=True, slots=True)
class AuthorizedProfileScope:
    membership: TenantMembership
    profile: AdvertisingProfile
    access_level: int


def require_membership(*, user, tenant_id) -> TenantMembership:
    membership = (
        TenantMembership.objects.select_related("tenant")
        .filter(
            tenant_id=tenant_id,
            user=user,
            is_active=True,
            tenant__is_active=True,
        )
        .first()
    )
    if membership is None:
        raise NotFound("卖家空间不存在或不在当前数据范围")
    return membership


def _is_tenant_manager(membership: TenantMembership) -> bool:
    return membership.membership_role in {
        MembershipRole.OWNER,
        MembershipRole.ADMIN,
    }


def _team_ids(membership: TenantMembership) -> QuerySet:
    return TeamMember.objects.filter(
        membership=membership,
        team__is_active=True,
    ).values_list("team_id", flat=True)


def feature_permission_codes(membership: TenantMembership) -> set[str]:
    if _is_tenant_manager(membership):
        return set(Permission.objects.values_list("code", flat=True))
    return set(
        Permission.objects.filter(
            role_permissions__role__user_roles__membership=membership,
            role_permissions__role__is_active=True,
        ).values_list("code", flat=True)
    )


def require_feature_permission(
    membership: TenantMembership,
    permission_code: str,
) -> None:
    if _is_tenant_manager(membership):
        return
    if not UserRole.objects.filter(
        membership=membership,
        role__is_active=True,
        role__role_permissions__permission__code=permission_code,
    ).exists():
        raise PermissionDenied("当前卖家空间内缺少功能权限")


def accessible_stores(
    *,
    membership: TenantMembership,
) -> QuerySet[AmazonStore]:
    base = AmazonStore.objects.filter(
        tenant=membership.tenant,
        is_active=True,
    )
    if _is_tenant_manager(membership):
        return base.order_by("name", "id")

    return (
        base.filter(
            Q(user_access_grants__user=membership.user)
            | Q(team_access_grants__team_id__in=_team_ids(membership))
        )
        .distinct()
        .order_by("name", "id")
    )


def profile_access_level(
    *,
    membership: TenantMembership,
    profile: AdvertisingProfile,
) -> int | None:
    if _is_tenant_manager(membership):
        return int(ProfileAccessLevel.MANAGE)

    direct = UserProfileAccess.objects.filter(
        user=membership.user,
        profile=profile,
    ).aggregate(level=Max("access_level"))["level"]
    team = TeamProfileAccess.objects.filter(
        team_id__in=_team_ids(membership),
        profile=profile,
    ).aggregate(level=Max("access_level"))["level"]
    levels = [level for level in (direct, team) if level is not None]
    return max(levels) if levels else None


def accessible_profiles(
    *,
    membership: TenantMembership,
    store_marketplace_id=None,
) -> list[tuple[AdvertisingProfile, int]]:
    profiles = AdvertisingProfile.objects.filter(
        store_marketplace__store__tenant=membership.tenant,
        store_marketplace__store__is_active=True,
        store_marketplace__is_active=True,
        is_active=True,
    ).select_related(
        "store_marketplace",
        "store_marketplace__store",
        "store_marketplace__marketplace",
    )
    if store_marketplace_id is not None:
        profiles = profiles.filter(store_marketplace_id=store_marketplace_id)

    store_ids = set(
        accessible_stores(membership=membership).values_list("id", flat=True)
    )
    result: list[tuple[AdvertisingProfile, int]] = []
    for profile in profiles.order_by("name", "id"):
        if profile.store_marketplace.store_id not in store_ids:
            continue
        level = profile_access_level(membership=membership, profile=profile)
        if level is not None:
            result.append((profile, level))
    return result


def require_profile_scope(
    *,
    user,
    tenant_id,
    profile_id,
    permission_code: str,
    minimum_level: ProfileAccessLevel,
) -> AuthorizedProfileScope:
    membership = require_membership(user=user, tenant_id=tenant_id)
    profile = (
        AdvertisingProfile.objects.select_related(
            "store_marketplace",
            "store_marketplace__store",
            "store_marketplace__marketplace",
        )
        .filter(
            pk=profile_id,
            store_marketplace__store__tenant=membership.tenant,
            store_marketplace__store__is_active=True,
            store_marketplace__is_active=True,
            is_active=True,
        )
        .first()
    )
    if profile is None:
        raise NotFound("AdvertisingProfile 不存在或不在当前数据范围")

    if not accessible_stores(membership=membership).filter(
        pk=profile.store_marketplace.store_id
    ).exists():
        raise NotFound("AdvertisingProfile 不存在或不在当前数据范围")

    level = profile_access_level(membership=membership, profile=profile)
    if level is None:
        raise NotFound("AdvertisingProfile 不存在或不在当前数据范围")

    require_feature_permission(membership, permission_code)
    if level < int(minimum_level):
        raise PermissionDenied("当前 AdvertisingProfile 权限等级不足")
    return AuthorizedProfileScope(
        membership=membership,
        profile=profile,
        access_level=level,
    )


def require_tenant_management(*, user, tenant_id) -> TenantMembership:
    membership = require_membership(user=user, tenant_id=tenant_id)
    require_feature_permission(membership, "rbac.manage")
    return membership


@transaction.atomic
def create_custom_role(
    *,
    request,
    tenant_id,
    name: str,
    code: str,
    permission_codes: list[str],
) -> Role:
    membership = require_tenant_management(user=request.user, tenant_id=tenant_id)
    requested = set(permission_codes)
    permissions = list(Permission.objects.filter(code__in=requested))
    found = {item.code for item in permissions}
    unknown = sorted(requested - found)
    if unknown:
        raise ValidationError(
            {"permission_codes": [f"未知权限码: {', '.join(unknown)}"]}
        )
    if Role.objects.filter(code=code).exists():
        raise ValidationError({"code": ["角色编码已存在"]})

    role = Role.objects.create(
        tenant=membership.tenant,
        name=name,
        code=code,
        is_system=False,
    )
    RolePermission.objects.bulk_create(
        [RolePermission(role=role, permission=permission) for permission in permissions]
    )
    append_audit_log(
        request=request,
        tenant=membership.tenant,
        actor=request.user,
        event="role.created",
        object_type="Role",
        object_id=role.pk,
        after_data={
            "name": role.name,
            "code": role.code,
            "permission_codes": sorted(found),
        },
    )
    return role


@transaction.atomic
def copy_role(
    *,
    request,
    tenant_id,
    source_role_id,
    name: str,
    code: str,
) -> Role:
    membership = require_tenant_management(user=request.user, tenant_id=tenant_id)
    source = (
        Role.objects.filter(
            Q(tenant=membership.tenant) | Q(tenant__isnull=True),
            pk=source_role_id,
            is_active=True,
        )
        .prefetch_related("role_permissions__permission")
        .first()
    )
    if source is None:
        raise NotFound("角色不存在或不在当前数据范围")
    return create_custom_role(
        request=request,
        tenant_id=tenant_id,
        name=name,
        code=code,
        permission_codes=[
            item.permission.code for item in source.role_permissions.all()
        ],
    )


@transaction.atomic
def deactivate_custom_role(*, request, tenant_id, role_id) -> Role:
    membership = require_tenant_management(user=request.user, tenant_id=tenant_id)
    role = (
        Role.objects.select_for_update()
        .filter(pk=role_id, tenant=membership.tenant, is_active=True)
        .first()
    )
    if role is None:
        if Role.objects.filter(pk=role_id, is_system=True).exists():
            raise PermissionDenied("系统内置角色不可删除")
        raise NotFound("角色不存在或不在当前数据范围")
    before = {"is_active": role.is_active}
    role.is_active = False
    role.save(update_fields=["is_active"])
    append_audit_log(
        request=request,
        tenant=membership.tenant,
        actor=request.user,
        event="role.deactivated",
        object_type="Role",
        object_id=role.pk,
        before_data=before,
        after_data={"is_active": False},
    )
    return role


def _authorized_user_for_tenant(*, tenant, user_id):
    user_model = get_user_model()
    user = user_model.objects.filter(
        pk=user_id,
        is_active=True,
        tenant_memberships__tenant=tenant,
        tenant_memberships__is_active=True,
    ).first()
    if user is None:
        raise NotFound("用户不存在或不在当前卖家空间")
    return user


def _authorized_team_for_tenant(*, tenant, team_id):
    team = Team.objects.filter(pk=team_id, tenant=tenant, is_active=True).first()
    if team is None:
        raise NotFound("Team 不存在或不在当前卖家空间")
    return team


@transaction.atomic
def grant_store_access(
    *,
    request,
    tenant_id,
    store_id,
    user_id=None,
    team_id=None,
):
    membership = require_tenant_management(user=request.user, tenant_id=tenant_id)
    if bool(user_id) == bool(team_id):
        raise ValidationError("user_id 与 team_id 必须且只能提供一个")
    store = AmazonStore.objects.filter(
        pk=store_id,
        tenant=membership.tenant,
        is_active=True,
    ).first()
    if store is None:
        raise NotFound("店铺不存在或不在当前数据范围")

    if user_id:
        grantee = _authorized_user_for_tenant(
            tenant=membership.tenant,
            user_id=user_id,
        )
        grant, created = UserStoreAccess.objects.get_or_create(
            user=grantee,
            store=store,
        )
        grantee_type = "User"
    else:
        grantee = _authorized_team_for_tenant(
            tenant=membership.tenant,
            team_id=team_id,
        )
        grant, created = TeamStoreAccess.objects.get_or_create(
            team=grantee,
            store=store,
        )
        grantee_type = "Team"
    if created:
        append_audit_log(
            request=request,
            tenant=membership.tenant,
            actor=request.user,
            event="store_access.granted",
            object_type="AmazonStore",
            object_id=store.pk,
            after_data={
                "grantee_type": grantee_type,
                "grantee_id": str(grantee.pk),
            },
        )
    return grant


@transaction.atomic
def grant_profile_access(
    *,
    request,
    tenant_id,
    profile_id,
    access_level: int,
    user_id=None,
    team_id=None,
):
    membership = require_tenant_management(user=request.user, tenant_id=tenant_id)
    if bool(user_id) == bool(team_id):
        raise ValidationError("user_id 与 team_id 必须且只能提供一个")
    if access_level not in ProfileAccessLevel.values:
        raise ValidationError({"access_level": ["无效的 Profile 权限等级"]})
    profile = AdvertisingProfile.objects.filter(
        pk=profile_id,
        store_marketplace__store__tenant=membership.tenant,
        is_active=True,
    ).first()
    if profile is None:
        raise NotFound("AdvertisingProfile 不存在或不在当前数据范围")

    if user_id:
        grantee = _authorized_user_for_tenant(
            tenant=membership.tenant,
            user_id=user_id,
        )
        grant, _ = UserProfileAccess.objects.update_or_create(
            user=grantee,
            profile=profile,
            defaults={"access_level": access_level},
        )
        grantee_type = "User"
    else:
        grantee = _authorized_team_for_tenant(
            tenant=membership.tenant,
            team_id=team_id,
        )
        grant, _ = TeamProfileAccess.objects.update_or_create(
            team=grantee,
            profile=profile,
            defaults={"access_level": access_level},
        )
        grantee_type = "Team"
    append_audit_log(
        request=request,
        tenant=membership.tenant,
        actor=request.user,
        event="profile_access.granted",
        object_type="AdvertisingProfile",
        object_id=profile.pk,
        after_data={
            "grantee_type": grantee_type,
            "grantee_id": str(grantee.pk),
            "access_level": ProfileAccessLevel(access_level).label,
        },
    )
    return grant
