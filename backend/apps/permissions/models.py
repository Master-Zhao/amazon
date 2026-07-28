import uuid

from django.conf import settings
from django.db import models

from apps.stores.models import AdvertisingProfile, AmazonStore
from apps.tenants.models import Team, Tenant


class ProfileAccessLevel(models.TextChoices):
    VIEW = "VIEW", "查看"
    OPERATE = "OPERATE", "操作"
    APPROVE = "APPROVE", "审批"
    EXECUTE = "EXECUTE", "执行"
    MANAGE = "MANAGE", "管理"


PROFILE_LEVEL_RANK = {
    ProfileAccessLevel.VIEW: 10,
    ProfileAccessLevel.OPERATE: 20,
    ProfileAccessLevel.APPROVE: 30,
    ProfileAccessLevel.EXECUTE: 40,
    ProfileAccessLevel.MANAGE: 50,
}


class Permission(models.Model):
    code = models.CharField(primary_key=True, max_length=64)
    name = models.CharField(max_length=128)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "sys_permission"


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, null=True, blank=True, on_delete=models.CASCADE, related_name="roles"
    )
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=128)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    permissions = models.ManyToManyField(
        Permission, through="RolePermission", related_name="roles"
    )

    class Meta:
        db_table = "org_role"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="org_role_tenant_code_uniq"
            )
        ]


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.PROTECT)

    class Meta:
        db_table = "org_role_permission"
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"], name="org_role_permission_uniq"
            )
        ]


class UserRole(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.PROTECT)

    class Meta:
        db_table = "org_user_role"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "user", "role"], name="org_user_role_uniq"
            )
        ]


class UserStoreAccess(models.Model):
    store = models.ForeignKey(AmazonStore, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        db_table = "ads_user_store_access"
        constraints = [
            models.UniqueConstraint(
                fields=["store", "user"], name="ads_user_store_access_uniq"
            )
        ]


class TeamStoreAccess(models.Model):
    store = models.ForeignKey(AmazonStore, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)

    class Meta:
        db_table = "ads_team_store_access"
        constraints = [
            models.UniqueConstraint(
                fields=["store", "team"], name="ads_team_store_access_uniq"
            )
        ]


class UserProfileAccess(models.Model):
    profile = models.ForeignKey(AdvertisingProfile, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    level = models.CharField(max_length=16, choices=ProfileAccessLevel.choices)

    class Meta:
        db_table = "ads_user_profile_access"
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "user"], name="ads_user_profile_access_uniq"
            )
        ]


class TeamProfileAccess(models.Model):
    profile = models.ForeignKey(AdvertisingProfile, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    level = models.CharField(max_length=16, choices=ProfileAccessLevel.choices)

    class Meta:
        db_table = "ads_team_profile_access"
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "team"], name="ads_team_profile_access_uniq"
            )
        ]

