import uuid

from django.db import models

from apps.products.models import ProductListing
from apps.stores.models import AdvertisingProfile


class AdType(models.TextChoices):
    SPONSORED_PRODUCTS = "SPONSORED_PRODUCTS", "Sponsored Products"
    SPONSORED_BRANDS = "SPONSORED_BRANDS", "Sponsored Brands (reserved)"
    SPONSORED_DISPLAY = "SPONSORED_DISPLAY", "Sponsored Display (reserved)"


class EntityState(models.TextChoices):
    ENABLED = "ENABLED", "Enabled"
    PAUSED = "PAUSED", "Paused"
    ARCHIVED = "ARCHIVED", "Archived"


class MatchType(models.TextChoices):
    BROAD = "BROAD", "Broad"
    PHRASE = "PHRASE", "Phrase"
    EXACT = "EXACT", "Exact"


class Campaign(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        AdvertisingProfile, on_delete=models.CASCADE, related_name="campaigns"
    )
    external_campaign_id = models.CharField(max_length=128)
    name = models.CharField(max_length=255)
    ad_type = models.CharField(
        max_length=32, choices=AdType.choices, default=AdType.SPONSORED_PRODUCTS
    )
    state = models.CharField(max_length=16, choices=EntityState.choices)
    daily_budget = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    currency = models.CharField(max_length=3)
    source_batch_id = models.UUIDField(null=True)

    class Meta:
        db_table = "ads_campaign"
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "external_campaign_id"],
                name="ads_campaign_profile_external_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["profile", "state"], name="ads_campaign_profile_state_idx")
        ]


class AdGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="ad_groups")
    external_ad_group_id = models.CharField(max_length=128)
    name = models.CharField(max_length=255)
    state = models.CharField(max_length=16, choices=EntityState.choices)

    class Meta:
        db_table = "ads_ad_group"
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "external_ad_group_id"],
                name="ads_adgroup_campaign_external_uniq",
            )
        ]


class Ad(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ad_group = models.ForeignKey(AdGroup, on_delete=models.CASCADE, related_name="ads")
    external_ad_id = models.CharField(max_length=128)
    listing = models.ForeignKey(
        ProductListing, null=True, blank=True, on_delete=models.SET_NULL, related_name="ads"
    )
    state = models.CharField(max_length=16, choices=EntityState.choices)

    class Meta:
        db_table = "ads_ad"
        constraints = [
            models.UniqueConstraint(
                fields=["ad_group", "external_ad_id"], name="ads_ad_group_external_uniq"
            )
        ]


class Keyword(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ad_group = models.ForeignKey(AdGroup, on_delete=models.CASCADE, related_name="keywords")
    external_keyword_id = models.CharField(max_length=128)
    text = models.CharField(max_length=255)
    match_type = models.CharField(max_length=16, choices=MatchType.choices)
    state = models.CharField(max_length=16, choices=EntityState.choices)
    bid = models.DecimalField(max_digits=14, decimal_places=2, null=True)

    class Meta:
        db_table = "ads_keyword"
        constraints = [
            models.UniqueConstraint(
                fields=["ad_group", "external_keyword_id"],
                name="ads_keyword_group_external_uniq",
            )
        ]


class ProductTarget(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ad_group = models.ForeignKey(AdGroup, on_delete=models.CASCADE, related_name="targets")
    external_target_id = models.CharField(max_length=128)
    expression = models.CharField(max_length=500)
    state = models.CharField(max_length=16, choices=EntityState.choices)
    bid = models.DecimalField(max_digits=14, decimal_places=2, null=True)

    class Meta:
        db_table = "ads_product_target"
        constraints = [
            models.UniqueConstraint(
                fields=["ad_group", "external_target_id"],
                name="ads_target_group_external_uniq",
            )
        ]


class NegativeKeyword(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        Campaign, null=True, blank=True, on_delete=models.CASCADE, related_name="negative_keywords"
    )
    ad_group = models.ForeignKey(
        AdGroup, null=True, blank=True, on_delete=models.CASCADE, related_name="negative_keywords"
    )
    text = models.CharField(max_length=255)
    match_type = models.CharField(max_length=16, choices=MatchType.choices)

    class Meta:
        db_table = "ads_negative_keyword"


class SearchTerm(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        AdvertisingProfile, on_delete=models.CASCADE, related_name="search_terms"
    )
    campaign = models.ForeignKey(
        Campaign, null=True, blank=True, on_delete=models.SET_NULL, related_name="search_terms"
    )
    ad_group = models.ForeignKey(
        AdGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="search_terms"
    )
    query_text = models.CharField(max_length=500)
    targeting_text = models.CharField(max_length=500, blank=True)
    source_batch_id = models.UUIDField(null=True)

    class Meta:
        db_table = "ads_search_term"
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "query_text", "targeting_text"],
                name="ads_search_term_profile_query_target_uniq",
            )
        ]

