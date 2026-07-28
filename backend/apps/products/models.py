from django.db import models

from apps.stores.models import Marketplace, StoreMarketplace
from apps.tenants.models import Tenant


class Product(models.Model):
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="products",
    )
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ads_product"
        indexes = [
            models.Index(
                fields=["tenant", "is_active"],
                name="ads_product_tenant_active_idx",
            )
        ]


class MarketplaceCatalogItem(models.Model):
    marketplace = models.ForeignKey(
        Marketplace,
        on_delete=models.PROTECT,
        related_name="catalog_items",
    )
    asin = models.CharField(max_length=32)
    title = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ads_marketplace_catalog_item"
        constraints = [
            models.UniqueConstraint(
                fields=["marketplace", "asin"],
                name="ads_catalog_market_asin_uniq",
            )
        ]


class ProductListing(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="listings",
    )
    store_marketplace = models.ForeignKey(
        StoreMarketplace,
        on_delete=models.PROTECT,
        related_name="product_listings",
    )
    catalog_item = models.ForeignKey(
        MarketplaceCatalogItem,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="listings",
    )
    seller_sku = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ads_product_listing"
        constraints = [
            models.UniqueConstraint(
                fields=["store_marketplace", "seller_sku"],
                name="ads_listing_store_market_sku_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["product", "is_active"],
                name="ads_listing_product_active_idx",
            )
        ]
