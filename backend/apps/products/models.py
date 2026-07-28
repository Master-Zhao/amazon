import uuid

from django.db import models

from apps.stores.models import Marketplace, StoreMarketplace
from apps.tenants.models import Tenant


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    internal_code = models.CharField(max_length=128)

    class Meta:
        db_table = "ads_product"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "internal_code"], name="ads_product_tenant_code_uniq"
            )
        ]


class MarketplaceCatalogItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    marketplace = models.ForeignKey(
        Marketplace, on_delete=models.PROTECT, related_name="catalog_items"
    )
    asin = models.CharField(max_length=32)
    title = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "ads_marketplace_catalog_item"
        constraints = [
            models.UniqueConstraint(
                fields=["marketplace", "asin"], name="ads_catalog_market_asin_uniq"
            )
        ]


class ProductListing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="listings")
    store_marketplace = models.ForeignKey(
        StoreMarketplace, on_delete=models.CASCADE, related_name="listings"
    )
    catalog_item = models.ForeignKey(
        MarketplaceCatalogItem,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="listings",
    )
    seller_sku = models.CharField(max_length=128)

    class Meta:
        db_table = "ads_product_listing"
        constraints = [
            models.UniqueConstraint(
                fields=["store_marketplace", "seller_sku"],
                name="ads_listing_scope_sku_uniq",
            )
        ]

