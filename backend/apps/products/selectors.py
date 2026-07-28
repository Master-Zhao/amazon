from apps.permissions.services import (
    require_feature_permission,
    require_membership,
)
from apps.products.models import Product


def product_rows(*, user, tenant_id) -> list[dict[str, object]]:
    membership = require_membership(user=user, tenant_id=tenant_id)
    require_feature_permission(membership, "products.view")
    products = Product.objects.filter(
        tenant=membership.tenant,
        is_active=True,
    ).prefetch_related(
        "listings__store_marketplace__store",
        "listings__store_marketplace__marketplace",
        "listings__catalog_item",
    )
    return [
        {
            "id": str(product.pk),
            "name": product.name,
            "is_active": product.is_active,
            "listings": [
                {
                    "id": str(listing.pk),
                    "store_marketplace_id": str(listing.store_marketplace_id),
                    "store_name": listing.store_marketplace.store.name,
                    "marketplace_code": listing.store_marketplace.marketplace.code,
                    "seller_sku": listing.seller_sku,
                    "asin": (
                        listing.catalog_item.asin
                        if listing.catalog_item_id
                        else None
                    ),
                    "catalog_title": (
                        listing.catalog_item.title
                        if listing.catalog_item_id
                        else ""
                    ),
                    "is_active": listing.is_active,
                }
                for listing in product.listings.all()
            ],
        }
        for product in products.order_by("name", "id")
    ]
