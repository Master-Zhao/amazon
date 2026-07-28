from django.db import models

from apps.tenants.models import Tenant


class Marketplace(models.Model):
    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=120)
    currency_code = models.CharField(max_length=3)
    timezone = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ads_marketplace"
        ordering = ["code"]


class AmazonStore(models.Model):
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="stores",
    )
    name = models.CharField(max_length=160)
    external_store_id = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ads_store"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "external_store_id"],
                name="ads_store_tenant_external_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["tenant", "is_active"],
                name="ads_store_tenant_active_idx",
            )
        ]

class StoreMarketplace(models.Model):
    store = models.ForeignKey(
        AmazonStore,
        on_delete=models.PROTECT,
        related_name="store_marketplaces",
    )
    marketplace = models.ForeignKey(
        Marketplace,
        on_delete=models.PROTECT,
        related_name="store_marketplaces",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ads_store_marketplace"
        constraints = [
            models.UniqueConstraint(
                fields=["store", "marketplace"],
                name="ads_store_marketplace_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["store", "is_active"],
                name="ads_store_market_active_idx",
            )
        ]


class AdvertisingProfile(models.Model):
    store_marketplace = models.ForeignKey(
        StoreMarketplace,
        on_delete=models.PROTECT,
        related_name="advertising_profiles",
    )
    external_profile_id = models.CharField(max_length=128)
    name = models.CharField(max_length=160)
    currency_code = models.CharField(max_length=3)
    timezone = models.CharField(max_length=64)
    target_acos = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ads_advertising_profile"
        constraints = [
            models.UniqueConstraint(
                fields=["store_marketplace", "external_profile_id"],
                name="ads_profile_store_market_ext_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["store_marketplace", "is_active"],
                name="ads_profile_store_active_idx",
            )
        ]
