from django.db.models import Q

from apps.permissions.models import (
    TeamProfileAccess,
    UserProfileAccess,
)
from apps.permissions.services import (
    accessible_store_ids,
    authorize,
    effective_profile_level,
    permission_codes_for,
)
from apps.stores.models import AdvertisingProfile, AmazonStore, StoreMarketplace
from apps.tenants.models import TeamMember, Tenant, TenantMembership


def tenant_contexts_for(user) -> list[dict]:
    memberships = (
        TenantMembership.objects.filter(
            user=user, is_active=True, tenant__is_active=True
        )
        .select_related("tenant")
        .order_by("tenant__name")
    )
    return [
        {
            "id": str(item.tenant_id),
            "name": item.tenant.name,
            "tenant_type": item.tenant.tenant_type,
            "membership_role": item.role,
            "permission_codes": sorted(
                permission_codes_for(user=user, tenant=item.tenant)
            ),
        }
        for item in memberships
    ]


def stores_for(*, user, tenant_id) -> list[dict]:
    context = authorize(user=user, tenant_id=tenant_id)
    store_ids = accessible_store_ids(user=user, tenant=context.membership.tenant)
    stores = AmazonStore.objects.filter(id__in=store_ids, is_active=True).order_by("name")
    return [
        {"id": str(store.pk), "name": store.name, "external_store_id": store.external_store_id}
        for store in stores
    ]


def store_marketplaces_for(*, user, tenant_id, store_id) -> list[dict]:
    try:
        store = AmazonStore.objects.get(pk=store_id)
    except (AmazonStore.DoesNotExist, ValueError) as exc:
        from rest_framework.exceptions import NotFound

        raise NotFound("店铺不存在") from exc
    authorize(user=user, tenant_id=tenant_id, store=store)
    scopes = (
        StoreMarketplace.objects.filter(store=store, is_active=True)
        .select_related("marketplace")
        .order_by("marketplace__code")
    )
    return [
        {
            "id": str(scope.pk),
            "marketplace": {
                "id": str(scope.marketplace_id),
                "code": scope.marketplace.code,
                "name": scope.marketplace.name,
                "country_code": scope.marketplace.country_code,
                "currency": scope.marketplace.currency,
                "timezone": scope.marketplace.timezone,
            },
        }
        for scope in scopes
    ]


def profiles_for(*, user, tenant_id, store_marketplace_id) -> list[dict]:
    try:
        scope = StoreMarketplace.objects.select_related("store").get(
            pk=store_marketplace_id, is_active=True
        )
    except (StoreMarketplace.DoesNotExist, ValueError) as exc:
        from rest_framework.exceptions import NotFound

        raise NotFound("站点范围不存在") from exc
    context = authorize(user=user, tenant_id=tenant_id, store=scope.store)
    membership = context.membership
    if membership.role in {"OWNER", "ADMIN"}:
        profiles = AdvertisingProfile.objects.filter(
            store_marketplace=scope, is_active=True
        )
    else:
        team_ids = TeamMember.objects.filter(
            membership=membership, team__is_active=True
        ).values_list("team_id", flat=True)
        profiles = AdvertisingProfile.objects.filter(
            Q(userprofileaccess__user=user)
            | Q(teamprofileaccess__team_id__in=team_ids),
            store_marketplace=scope,
            is_active=True,
        ).distinct()
    return [
        {
            "id": str(profile.pk),
            "external_profile_id": profile.external_profile_id,
            "name": profile.name,
            "currency": profile.currency,
            "timezone": profile.timezone,
            "access_level": effective_profile_level(user=user, profile=profile),
        }
        for profile in profiles.order_by("name")
    ]

