from django.db import transaction
from rest_framework.exceptions import NotFound
from rest_framework.serializers import ValidationError

from apps.audit.services import append_audit_log
from apps.permissions.services import (
    accessible_stores,
    require_feature_permission,
    require_membership,
)
from apps.products.models import (
    MarketplaceCatalogItem,
    Product,
    ProductListing,
)
from apps.stores.models import StoreMarketplace


def _store_marketplace_scope(*, membership, store_marketplace_id):
    store_marketplace = (
        StoreMarketplace.objects.select_related("store", "marketplace")
        .filter(
            pk=store_marketplace_id,
            store__tenant=membership.tenant,
            store__is_active=True,
            is_active=True,
        )
        .first()
    )
    if store_marketplace is None:
        raise NotFound("StoreMarketplace does not exist in the current scope.")
    if not accessible_stores(membership=membership).filter(
        pk=store_marketplace.store_id
    ).exists():
        raise NotFound("StoreMarketplace does not exist in the current scope.")
    return store_marketplace


def _listing_values(
    *,
    membership,
    store_marketplace_id,
    seller_sku: str,
    asin: str | None,
    catalog_title: str,
):
    store_marketplace = _store_marketplace_scope(
        membership=membership,
        store_marketplace_id=store_marketplace_id,
    )
    normalized_sku = seller_sku.strip()
    if not normalized_sku:
        raise ValidationError({"seller_sku": ["This field is required."]})
    if ProductListing.objects.filter(
        store_marketplace=store_marketplace,
        seller_sku=normalized_sku,
    ).exists():
        raise ValidationError(
            {"seller_sku": ["This SKU already exists in the StoreMarketplace."]}
        )
    catalog_item = None
    if asin and asin.strip():
        normalized_asin = asin.strip().upper()
        catalog_item, _ = MarketplaceCatalogItem.objects.get_or_create(
            marketplace=store_marketplace.marketplace,
            asin=normalized_asin,
            defaults={"title": catalog_title.strip()},
        )
    return store_marketplace, normalized_sku, catalog_item


@transaction.atomic
def create_product(
    *,
    request,
    tenant_id,
    name: str,
    store_marketplace_id,
    seller_sku: str,
    asin: str | None = None,
    catalog_title: str = "",
) -> Product:
    membership = require_membership(user=request.user, tenant_id=tenant_id)
    require_feature_permission(membership, "products.manage")
    normalized_name = name.strip()
    if not normalized_name:
        raise ValidationError({"name": ["This field is required."]})
    store_marketplace, normalized_sku, catalog_item = _listing_values(
        membership=membership,
        store_marketplace_id=store_marketplace_id,
        seller_sku=seller_sku,
        asin=asin,
        catalog_title=catalog_title,
    )
    product = Product.objects.create(
        tenant=membership.tenant,
        name=normalized_name,
    )
    listing = ProductListing.objects.create(
        product=product,
        store_marketplace=store_marketplace,
        catalog_item=catalog_item,
        seller_sku=normalized_sku,
    )
    append_audit_log(
        request=request,
        tenant=membership.tenant,
        actor=request.user,
        event="product.created",
        object_type="Product",
        object_id=product.pk,
        after_data={
            "name": product.name,
            "listing_id": str(listing.pk),
            "store_marketplace_id": str(store_marketplace.pk),
            "seller_sku": normalized_sku,
            "asin": catalog_item.asin if catalog_item else None,
        },
    )
    return product


@transaction.atomic
def add_product_listing(
    *,
    request,
    tenant_id,
    product_id,
    store_marketplace_id,
    seller_sku: str,
    asin: str | None = None,
    catalog_title: str = "",
) -> Product:
    membership = require_membership(user=request.user, tenant_id=tenant_id)
    require_feature_permission(membership, "products.manage")
    product = Product.objects.select_for_update().filter(
        pk=product_id,
        tenant=membership.tenant,
        is_active=True,
    ).first()
    if product is None:
        raise NotFound("Product does not exist in the current tenant scope.")
    store_marketplace, normalized_sku, catalog_item = _listing_values(
        membership=membership,
        store_marketplace_id=store_marketplace_id,
        seller_sku=seller_sku,
        asin=asin,
        catalog_title=catalog_title,
    )
    listing = ProductListing.objects.create(
        product=product,
        store_marketplace=store_marketplace,
        catalog_item=catalog_item,
        seller_sku=normalized_sku,
    )
    append_audit_log(
        request=request,
        tenant=membership.tenant,
        actor=request.user,
        event="product.listing_added",
        object_type="Product",
        object_id=product.pk,
        after_data={
            "listing_id": str(listing.pk),
            "store_marketplace_id": str(store_marketplace.pk),
            "seller_sku": normalized_sku,
            "asin": catalog_item.asin if catalog_item else None,
        },
    )
    return product
