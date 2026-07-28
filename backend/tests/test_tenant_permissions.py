import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

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
    authorize,
    create_role,
    effective_profile_level,
    grant_user_profile_access,
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


@pytest.fixture
def organization(db):
    user_model = get_user_model()
    owner = user_model.objects.create_user(
        username="owner", email="owner@example.invalid", password="password"
    )
    member = user_model.objects.create_user(
        username="member", email="member@example.invalid", password="password"
    )
    outsider = user_model.objects.create_user(
        username="outsider", email="outsider@example.invalid", password="password"
    )
    tenant = Tenant.objects.create(name="Tenant A", tenant_type=TenantType.TEAM)
    other_tenant = Tenant.objects.create(
        name="Tenant B", tenant_type=TenantType.COMPANY
    )
    TenantMembership.objects.create(
        tenant=tenant, user=owner, role=MembershipRole.OWNER
    )
    member_membership = TenantMembership.objects.create(
        tenant=tenant, user=member, role=MembershipRole.MEMBER
    )
    TenantMembership.objects.create(
        tenant=other_tenant, user=outsider, role=MembershipRole.OWNER
    )
    marketplace = Marketplace.objects.create(
        code="US",
        name="Amazon.com",
        country_code="US",
        currency="USD",
        timezone="America/Los_Angeles",
    )
    store = AmazonStore.objects.create(
        tenant=tenant, name="Store A", external_store_id="STORE-A"
    )
    other_store = AmazonStore.objects.create(
        tenant=other_tenant, name="Store B", external_store_id="STORE-B"
    )
    scope = StoreMarketplace.objects.create(
        store=store, marketplace=marketplace, seller_id="SELLER-A"
    )
    other_scope = StoreMarketplace.objects.create(
        store=other_store, marketplace=marketplace, seller_id="SELLER-B"
    )
    profile = AdvertisingProfile.objects.create(
        store_marketplace=scope,
        external_profile_id="PROFILE-A",
        name="Profile A",
        currency="USD",
        timezone=marketplace.timezone,
    )
    other_profile = AdvertisingProfile.objects.create(
        store_marketplace=other_scope,
        external_profile_id="PROFILE-B",
        name="Profile B",
        currency="USD",
        timezone=marketplace.timezone,
    )
    team = Team.objects.create(tenant=tenant, name="Operators")
    TeamMember.objects.create(team=team, membership=member_membership)
    return {
        "owner": owner,
        "member": member,
        "outsider": outsider,
        "tenant": tenant,
        "other_tenant": other_tenant,
        "store": store,
        "other_store": other_store,
        "scope": scope,
        "profile": profile,
        "other_profile": other_profile,
        "team": team,
    }


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.mark.django_db
def test_owner_sees_all_context_and_string_ids(organization):
    org = organization
    client = authenticated_client(org["owner"])

    tenants = client.get("/api/v1/context/tenants")
    stores = client.get(f"/api/v1/context/tenants/{org['tenant'].pk}/stores")
    scopes = client.get(
        f"/api/v1/context/tenants/{org['tenant'].pk}/stores/{org['store'].pk}/marketplaces"
    )
    profiles = client.get(
        f"/api/v1/context/tenants/{org['tenant'].pk}/store-marketplaces/{org['scope'].pk}/profiles"
    )

    assert tenants.status_code == stores.status_code == scopes.status_code == profiles.status_code == 200
    assert tenants.json()["data"]["items"][0]["id"] == str(org["tenant"].pk)
    assert stores.json()["data"]["items"][0]["id"] == str(org["store"].pk)
    assert profiles.json()["data"]["items"][0]["accessLevel"] == "MANAGE"


@pytest.mark.django_db
def test_member_store_access_is_union_of_direct_and_team(organization):
    org = organization
    second = AmazonStore.objects.create(
        tenant=org["tenant"], name="Store A2", external_store_id="STORE-A2"
    )
    UserStoreAccess.objects.create(user=org["member"], store=org["store"])
    TeamStoreAccess.objects.create(team=org["team"], store=second)

    response = authenticated_client(org["member"]).get(
        f"/api/v1/context/tenants/{org['tenant'].pk}/stores"
    )

    assert response.status_code == 200
    assert {item["id"] for item in response.json()["data"]["items"]} == {
        str(org["store"].pk),
        str(second.pk),
    }


@pytest.mark.django_db
def test_profile_access_uses_highest_direct_or_team_level(organization):
    org = organization
    UserStoreAccess.objects.create(user=org["member"], store=org["store"])
    UserProfileAccess.objects.create(
        user=org["member"], profile=org["profile"], level=ProfileAccessLevel.VIEW
    )
    TeamProfileAccess.objects.create(
        team=org["team"], profile=org["profile"], level=ProfileAccessLevel.EXECUTE
    )

    assert (
        effective_profile_level(user=org["member"], profile=org["profile"])
        == ProfileAccessLevel.EXECUTE
    )


@pytest.mark.django_db
def test_cross_tenant_and_no_data_scope_return_404(organization):
    org = organization
    client = authenticated_client(org["member"])

    cross_tenant = client.get(
        f"/api/v1/context/tenants/{org['other_tenant'].pk}/stores"
    )
    no_store_scope = client.get(
        f"/api/v1/context/tenants/{org['tenant'].pk}/stores/{org['store'].pk}/marketplaces"
    )

    assert cross_tenant.status_code == 404
    assert no_store_scope.status_code == 404


@pytest.mark.django_db
def test_missing_function_permission_is_403_inside_current_tenant(organization):
    org = organization
    with pytest.raises(Exception) as error:
        authorize(
            user=org["member"],
            tenant_id=org["tenant"].pk,
            permission_code="reports.import",
        )
    assert getattr(error.value, "status_code", None) == 403


@pytest.mark.django_db
def test_custom_role_can_only_combine_existing_permission_codes(organization):
    org = organization
    with pytest.raises(ValueError):
        create_role(
            actor=org["owner"],
            tenant=org["tenant"],
            code="bad",
            name="Bad",
            permission_codes=["invented.permission"],
        )


@pytest.mark.django_db
def test_custom_role_grants_function_permission(organization):
    org = organization
    role = create_role(
        actor=org["owner"],
        tenant=org["tenant"],
        code="report_reader",
        name="Report Reader",
        permission_codes=["reports.view"],
    )
    UserRole.objects.create(
        tenant=org["tenant"], user=org["member"], role=role
    )

    context = authorize(
        user=org["member"],
        tenant_id=org["tenant"].pk,
        permission_code="reports.view",
    )

    assert "reports.view" in context.permission_codes


@pytest.mark.django_db
def test_inactive_membership_is_not_authorized(organization):
    org = organization
    TenantMembership.objects.filter(
        tenant=org["tenant"], user=org["member"]
    ).update(is_active=False)

    response = authenticated_client(org["member"]).get(
        f"/api/v1/context/tenants/{org['tenant'].pk}/stores"
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_personal_tenant_does_not_require_team(db):
    user = get_user_model().objects.create_user(
        username="personal", email="personal@example.invalid", password="password"
    )
    tenant = Tenant.objects.create(
        name="Personal", tenant_type=TenantType.PERSONAL
    )
    TenantMembership.objects.create(
        tenant=tenant, user=user, role=MembershipRole.OWNER
    )

    assert Team.objects.filter(tenant=tenant).count() == 0
    assert authenticated_client(user).get("/api/v1/context/tenants").status_code == 200


@pytest.mark.django_db
def test_owner_can_grant_profile_and_store_scope_atomically(organization):
    org = organization

    grant = grant_user_profile_access(
        actor=org["owner"],
        tenant=org["tenant"],
        profile=org["profile"],
        user_id=org["member"].pk,
        level=ProfileAccessLevel.OPERATE,
    )

    assert grant.level == ProfileAccessLevel.OPERATE
    assert UserStoreAccess.objects.filter(
        user=org["member"], store=org["store"]
    ).exists()


@pytest.mark.django_db
def test_profile_grant_rejects_cross_tenant_object(organization):
    org = organization

    with pytest.raises(Exception) as error:
        grant_user_profile_access(
            actor=org["owner"],
            tenant=org["tenant"],
            profile=org["other_profile"],
            user_id=org["member"].pk,
            level=ProfileAccessLevel.VIEW,
        )

    assert getattr(error.value, "status_code", None) == 404
