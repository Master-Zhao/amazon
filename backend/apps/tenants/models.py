import uuid

from django.conf import settings
from django.db import models


class TenantType(models.TextChoices):
    PERSONAL = "PERSONAL", "个人"
    TEAM = "TEAM", "团队"
    COMPANY = "COMPANY", "公司"


class MembershipRole(models.TextChoices):
    OWNER = "OWNER", "所有者"
    ADMIN = "ADMIN", "管理员"
    MEMBER = "MEMBER", "成员"


class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)
    tenant_type = models.CharField(max_length=16, choices=TenantType.choices)
    target_acos = models.DecimalField(
        max_digits=7, decimal_places=4, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "org_tenant"


class TenantMembership(models.Model):
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tenant_memberships",
    )
    role = models.CharField(
        max_length=16, choices=MembershipRole.choices, default=MembershipRole.MEMBER
    )
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "org_tenant_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "user"], name="org_membership_tenant_user_uniq"
            )
        ]
        indexes = [
            models.Index(
                fields=["user", "is_active"], name="org_membership_user_active_idx"
            )
        ]


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="teams")
    name = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "org_team"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"], name="org_team_tenant_name_uniq"
            )
        ]


class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="members")
    membership = models.ForeignKey(
        TenantMembership, on_delete=models.CASCADE, related_name="team_memberships"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "org_team_member"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "membership"], name="org_team_member_uniq"
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.team_id and self.membership_id:
            if self.team.tenant_id != self.membership.tenant_id:
                raise ValidationError("Team and membership must belong to the same tenant")

