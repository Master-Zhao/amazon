import uuid

from django.db import models

from apps.tenants.models import Tenant


class AmazonStore(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="stores")
    name = models.CharField(max_length=128)
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
            models.Index(fields=["tenant", "is_active"], name="ads_store_tenant_active_idx")
        ]


class Marketplace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    country_code = models.CharField(max_length=2)
    currency = models.CharField(max_length=3)
    timezone = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ads_marketplace"


class StoreMarketplace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        AmazonStore, on_delete=models.CASCADE, related_name="store_marketplaces"
    )
    marketplace = models.ForeignKey(
        Marketplace, on_delete=models.PROTECT, related_name="store_marketplaces"
    )
    seller_id = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ads_store_marketplace"
        constraints = [
            models.UniqueConstraint(
                fields=["store", "marketplace"],
                name="ads_store_marketplace_uniq",
            )
        ]


class AdvertisingProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_marketplace = models.ForeignKey(
        StoreMarketplace, on_delete=models.CASCADE, related_name="profiles"
    )
    external_profile_id = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    account_type = models.CharField(max_length=32, default="SELLER")
    currency = models.CharField(max_length=3)
    timezone = models.CharField(max_length=64)
    target_acos = models.DecimalField(
        max_digits=7, decimal_places=4, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ads_advertising_profile"
        constraints = [
            models.UniqueConstraint(
                fields=["store_marketplace", "external_profile_id"],
                name="ads_profile_scope_external_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["store_marketplace", "is_active"],
                name="ads_profile_scope_active_idx",
            )
        ]

