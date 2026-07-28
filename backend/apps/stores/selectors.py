from apps.permissions.models import ProfileAccessLevel
from apps.permissions.services import (
    accessible_profiles,
    accessible_stores,
    feature_permission_codes,
    require_membership,
)
from apps.stores.models import StoreMarketplace
from apps.tenants.selectors import memberships_for_user


def tenant_options(user) -> list[dict]:
    return [
        {
            "id": str(membership.tenant_id),
            "name": membership.tenant.name,
            "tenant_type": membership.tenant.tenant_type,
            "membership_role": membership.membership_role,
        }
        for membership in memberships_for_user(user)
    ]


def store_options(*, user, tenant_id) -> list[dict]:
    membership = require_membership(user=user, tenant_id=tenant_id)
    return [
        {
            "id": str(store.id),
            "name": store.name,
            "external_store_id": store.external_store_id,
        }
        for store in accessible_stores(membership=membership)
    ]


def marketplace_options(*, user, tenant_id, store_id) -> list[dict]:
    membership = require_membership(user=user, tenant_id=tenant_id)
    if not accessible_stores(membership=membership).filter(pk=store_id).exists():
        from rest_framework.exceptions import NotFound

        raise NotFound("店铺不存在或不在当前数据范围")

    return [
        {
            "store_marketplace_id": str(item.id),
            "marketplace": {
                "id": str(item.marketplace_id),
                "code": item.marketplace.code,
                "name": item.marketplace.name,
                "currency_code": item.marketplace.currency_code,
                "timezone": item.marketplace.timezone,
            },
        }
        for item in StoreMarketplace.objects.filter(
            store_id=store_id,
            is_active=True,
            marketplace__is_active=True,
        )
        .select_related("marketplace")
        .order_by("marketplace__code")
    ]


def profile_options(*, user, tenant_id, store_marketplace_id) -> list[dict]:
    membership = require_membership(user=user, tenant_id=tenant_id)
    options = []
    for profile, level in accessible_profiles(
        membership=membership,
        store_marketplace_id=store_marketplace_id,
    ):
        options.append(
            {
                "id": str(profile.id),
                "name": profile.name,
                "external_profile_id": profile.external_profile_id,
                "currency_code": profile.currency_code,
                "timezone": profile.timezone,
                "access_level": ProfileAccessLevel(level).label,
            }
        )
    return options


def context_capabilities(*, user, tenant_id) -> dict:
    membership = require_membership(user=user, tenant_id=tenant_id)
    return {
        "permission_codes": sorted(feature_permission_codes(membership)),
        "membership_role": membership.membership_role,
    }
