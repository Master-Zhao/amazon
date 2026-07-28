from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.stores.models import AdvertisingProfile, AmazonStore
from apps.tenants.models import Team, Tenant, TenantMembership


class ProfileAccessLevel(models.IntegerChoices):
    VIEW = 10, "VIEW"
    OPERATE = 20, "OPERATE"
    APPROVE = 30, "APPROVE"
    EXECUTE = 40, "EXECUTE"
    MANAGE = 50, "MANAGE"


class Permission(models.Model):
    code = models.CharField(max_length=96, unique=True)
    name = models.CharField(max_length=160)
    description = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "sys_permission"
        ordering = ["code"]


class Role(models.Model):
    tenant = models.ForeignKey(
        Tenant,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="roles",
    )
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=96, unique=True)
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "org_role"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(is_system=True, tenant__isnull=True)
                    | Q(is_system=False, tenant__isnull=False)
                ),
                name="org_role_system_tenant_ck",
            ),
        ]


class RolePermission(models.Model):
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="role_permissions",
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.PROTECT,
        related_name="role_permissions",
    )

    class Meta:
        db_table = "org_role_permission"
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="org_role_permission_uniq",
            )
        ]


class UserRole(models.Model):
    membership = models.ForeignKey(
        TenantMembership,
        on_delete=models.PROTECT,
        related_name="user_roles",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="user_roles",
    )

    class Meta:
        db_table = "org_user_role"
        constraints = [
            models.UniqueConstraint(
                fields=["membership", "role"],
                name="org_user_role_uniq",
            )
        ]


class UserStoreAccess(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="store_access_grants",
    )
    store = models.ForeignKey(
        AmazonStore,
        on_delete=models.PROTECT,
        related_name="user_access_grants",
    )

    class Meta:
        db_table = "org_user_store_access"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "store"],
                name="org_user_store_access_uniq",
            )
        ]


class TeamStoreAccess(models.Model):
    team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="store_access_grants",
    )
    store = models.ForeignKey(
        AmazonStore,
        on_delete=models.PROTECT,
        related_name="team_access_grants",
    )

    class Meta:
        db_table = "org_team_store_access"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "store"],
                name="org_team_store_access_uniq",
            )
        ]


class UserProfileAccess(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="profile_access_grants",
    )
    profile = models.ForeignKey(
        AdvertisingProfile,
        on_delete=models.PROTECT,
        related_name="user_access_grants",
    )
    access_level = models.PositiveSmallIntegerField(
        choices=ProfileAccessLevel.choices
    )

    class Meta:
        db_table = "org_user_profile_access"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "profile"],
                name="org_user_profile_access_uniq",
            )
        ]


class TeamProfileAccess(models.Model):
    team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="profile_access_grants",
    )
    profile = models.ForeignKey(
        AdvertisingProfile,
        on_delete=models.PROTECT,
        related_name="team_access_grants",
    )
    access_level = models.PositiveSmallIntegerField(
        choices=ProfileAccessLevel.choices
    )

    class Meta:
        db_table = "org_team_profile_access"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "profile"],
                name="org_team_profile_access_uniq",
            )
        ]
