import pytest
from django.core.exceptions import ValidationError
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
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
from apps.permissions.services import (
    accessible_profiles,
    accessible_stores,
    profile_access_level,
    require_profile_scope,
)
from apps.stores.models import (
    AdvertisingProfile,
    AmazonStore,
    Marketplace,
    StoreMarketplace,
)
from apps.tenants.models import (
    MembershipRole,
    Team,
    TeamMember,
    Tenant,
    TenantMembership,
    TenantType,
)

pytestmark = pytest.mark.django_db


def build_scope(*, email="member@example.invalid", role=MembershipRole.MEMBER):
    user = User.objects.create_user(
        username=email.split("@")[0],
        email=email,
        password="not-a-demo-secret",
    )
    tenant = Tenant.objects.create(name=f"{email} tenant", tenant_type=TenantType.TEAM)
    membership = TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        membership_role=role,
    )
    marketplace = Marketplace.objects.create(
        code=f"M{tenant.pk}",
        name="Fixture Marketplace",
        currency_code="USD",
        timezone="UTC",
    )
    store = AmazonStore.objects.create(
        tenant=tenant,
        name="Fixture Store",
        external_store_id=f"store-{tenant.pk}",
    )
    store_marketplace = StoreMarketplace.objects.create(
        store=store,
        marketplace=marketplace,
    )
    profile = AdvertisingProfile.objects.create(
        store_marketplace=store_marketplace,
        external_profile_id=f"profile-{tenant.pk}",
        name="Fixture Profile",
        currency_code="USD",
        timezone="UTC",
    )
    return user, tenant, membership, marketplace, store, store_marketplace, profile


def grant_feature(membership, code):
    permission, _ = Permission.objects.update_or_create(
        code=code,
        defaults={"name": code, "description": code},
    )
    role = Role.objects.create(
        tenant=membership.tenant,
        name="Fixture role",
        code=f"role-{membership.pk}",
    )
    RolePermission.objects.create(role=role, permission=permission)
    UserRole.objects.create(membership=membership, role=role)


def test_owner_has_all_store_and_manage_profile_access():
    user, tenant, membership, _, store, _, profile = build_scope(
        email="owner@example.invalid",
        role=MembershipRole.OWNER,
    )
    Permission.objects.update_or_create(
        code="reports.upload",
        defaults={"name": "Upload", "description": "Upload"},
    )

    assert list(accessible_stores(membership=membership)) == [store]
    assert accessible_profiles(membership=membership) == [
        (profile, int(ProfileAccessLevel.MANAGE))
    ]
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        permission_code="reports.upload",
        minimum_level=ProfileAccessLevel.OPERATE,
    )
    assert scope.profile == profile


def test_direct_and_team_grants_form_union_and_highest_profile_level():
    user, _, membership, _, store, _, profile = build_scope()
    second_store = AmazonStore.objects.create(
        tenant=membership.tenant,
        name="Team Store",
        external_store_id="team-store",
    )
    team = Team.objects.create(tenant=membership.tenant, name="Analysts")
    TeamMember.objects.create(team=team, membership=membership)
    UserStoreAccess.objects.create(user=user, store=store)
    TeamStoreAccess.objects.create(team=team, store=second_store)
    UserProfileAccess.objects.create(
        user=user,
        profile=profile,
        access_level=ProfileAccessLevel.VIEW,
    )
    TeamProfileAccess.objects.create(
        team=team,
        profile=profile,
        access_level=ProfileAccessLevel.APPROVE,
    )

    assert set(accessible_stores(membership=membership)) == {store, second_store}
    assert profile_access_level(membership=membership, profile=profile) == int(
        ProfileAccessLevel.APPROVE
    )


def test_cross_tenant_profile_is_hidden_with_404():
    user, tenant, membership, _, store, _, _ = build_scope()
    UserStoreAccess.objects.create(user=user, store=store)
    other = build_scope(email="other@example.invalid")
    grant_feature(membership, "reports.upload")

    with pytest.raises(NotFound):
        require_profile_scope(
            user=user,
            tenant_id=tenant.pk,
            profile_id=other[-1].pk,
            permission_code="reports.upload",
            minimum_level=ProfileAccessLevel.OPERATE,
        )


def test_in_scope_but_insufficient_level_is_403():
    user, tenant, membership, _, store, _, profile = build_scope()
    UserStoreAccess.objects.create(user=user, store=store)
    UserProfileAccess.objects.create(
        user=user,
        profile=profile,
        access_level=ProfileAccessLevel.VIEW,
    )
    grant_feature(membership, "reports.upload")

    with pytest.raises(PermissionDenied):
        require_profile_scope(
            user=user,
            tenant_id=tenant.pk,
            profile_id=profile.pk,
            permission_code="reports.upload",
            minimum_level=ProfileAccessLevel.OPERATE,
        )


def test_missing_feature_permission_is_403():
    user, tenant, membership, _, store, _, profile = build_scope()
    UserStoreAccess.objects.create(user=user, store=store)
    UserProfileAccess.objects.create(
        user=user,
        profile=profile,
        access_level=ProfileAccessLevel.MANAGE,
    )

    with pytest.raises(PermissionDenied):
        require_profile_scope(
            user=user,
            tenant_id=tenant.pk,
            profile_id=profile.pk,
            permission_code="reports.upload",
            minimum_level=ProfileAccessLevel.VIEW,
        )


def test_analytics_configuration_requires_feature_permission():
    user, tenant, membership, _, store, _, profile = build_scope()
    UserStoreAccess.objects.create(user=user, store=store)
    UserProfileAccess.objects.create(
        user=user,
        profile=profile,
        access_level=ProfileAccessLevel.MANAGE,
    )
    grant_feature(membership, "analytics.view")
    client = APIClient()
    client.force_authenticate(user)

    readable = client.get(
        f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{profile.pk}/"
        "configuration"
    )
    denied = client.put(
        f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{profile.pk}/"
        "configuration/target-acos",
        {"scopeType": "PROFILE", "targetAcos": "0.2500"},
        format="json",
    )

    assert readable.status_code == 200
    assert denied.status_code == 403


def test_team_member_rejects_cross_tenant_membership():
    _, _, membership, _, _, _, _ = build_scope()
    other = build_scope(email="other-team@example.invalid")
    team = Team.objects.create(tenant=other[1], name="Other tenant team")
    item = TeamMember(team=team, membership=membership)
    with pytest.raises(ValidationError):
        item.full_clean()


def test_context_api_returns_string_ids_and_camel_case():
    user, tenant, _, marketplace, store, store_marketplace, profile = build_scope(
        role=MembershipRole.OWNER
    )
    Permission.objects.update_or_create(
        code="context.view",
        defaults={"name": "Context", "description": "Context"},
    )
    client = APIClient()
    client.force_authenticate(user)

    tenants = client.get("/api/v1/context/tenants")
    assert tenants.status_code == 200
    assert tenants.json()["data"][0]["id"] == str(tenant.pk)
    assert tenants.json()["data"][0]["tenantType"] == TenantType.TEAM

    stores = client.get(f"/api/v1/context/tenants/{tenant.pk}/stores")
    assert stores.json()["data"][0]["id"] == str(store.pk)

    marketplaces = client.get(
        f"/api/v1/context/tenants/{tenant.pk}/stores/{store.pk}/marketplaces"
    )
    assert marketplaces.json()["data"][0]["storeMarketplaceId"] == str(
        store_marketplace.pk
    )
    assert marketplaces.json()["data"][0]["marketplace"]["code"] == marketplace.code

    profiles = client.get(
        f"/api/v1/context/tenants/{tenant.pk}/store-marketplaces/"
        f"{store_marketplace.pk}/profiles"
    )
    assert profiles.json()["data"][0]["id"] == str(profile.pk)
    assert profiles.json()["data"][0]["accessLevel"] == "MANAGE"


def test_owner_can_manage_roles_and_grants_with_append_only_audit():
    owner, tenant, _, _, store, _, profile = build_scope(
        email="manager@example.invalid",
        role=MembershipRole.OWNER,
    )
    member = User.objects.create_user(
        username="grantee",
        email="grantee@example.invalid",
        password="not-a-demo-secret",
    )
    target_membership = TenantMembership.objects.create(
        tenant=tenant,
        user=member,
        membership_role=MembershipRole.MEMBER,
    )
    Permission.objects.update_or_create(
        code="rbac.manage",
        defaults={"name": "Manage", "description": "Manage"},
    )
    Permission.objects.update_or_create(
        code="reports.upload",
        defaults={"name": "Upload", "description": "Upload"},
    )
    client = APIClient()
    client.force_authenticate(owner)

    role_response = client.post(
        f"/api/v1/access/tenants/{tenant.pk}/roles",
        {
            "name": "Report operator",
            "code": f"report-operator-{tenant.pk}",
            "permissionCodes": ["reports.upload"],
        },
        format="json",
    )
    assert role_response.status_code == 201
    role_id = role_response.json()["data"]["id"]

    assign_response = client.post(
        f"/api/v1/access/tenants/{tenant.pk}/member-roles",
        {"membershipId": str(target_membership.pk), "roleId": role_id},
        format="json",
    )
    assert assign_response.status_code == 201

    store_response = client.post(
        f"/api/v1/access/tenants/{tenant.pk}/store-access",
        {"storeId": str(store.pk), "userId": str(member.pk)},
        format="json",
    )
    assert store_response.status_code == 201

    profile_response = client.post(
        f"/api/v1/access/tenants/{tenant.pk}/profile-access",
        {
            "profileId": str(profile.pk),
            "userId": str(member.pk),
            "accessLevel": "OPERATE",
        },
        format="json",
    )
    assert profile_response.status_code == 201
    assert AuditLog.objects.filter(tenant=tenant).count() == 4

    audit = AuditLog.objects.filter(tenant=tenant).first()
    audit.event = "tampered"
    with pytest.raises(TypeError):
        audit.save()
    with pytest.raises(TypeError):
        audit.delete()


def test_system_role_can_be_copied_but_not_deleted():
    owner, tenant, _, _, _, _, _ = build_scope(
        email="system-role-owner@example.invalid",
        role=MembershipRole.OWNER,
    )
    Permission.objects.update_or_create(
        code="rbac.manage",
        defaults={"name": "Manage", "description": "Manage"},
    )
    permission, _ = Permission.objects.update_or_create(
        code="analytics.view",
        defaults={"name": "Analytics", "description": "Analytics"},
    )
    system_role = Role.objects.create(
        tenant=None,
        name="System analyst",
        code=f"system-analyst-{tenant.pk}",
        is_system=True,
    )
    RolePermission.objects.create(role=system_role, permission=permission)
    client = APIClient()
    client.force_authenticate(owner)

    copied = client.post(
        f"/api/v1/access/tenants/{tenant.pk}/roles/{system_role.pk}/copy",
        {
            "name": "Tenant analyst",
            "code": f"tenant-analyst-{tenant.pk}",
        },
        format="json",
    )
    assert copied.status_code == 201

    denied = client.delete(
        f"/api/v1/access/tenants/{tenant.pk}/roles/{system_role.pk}"
    )
    assert denied.status_code == 403
