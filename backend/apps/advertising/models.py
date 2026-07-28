from django.db import models

from apps.products.models import ProductListing
from apps.stores.models import AdvertisingProfile


class AdProductType(models.TextChoices):
    SPONSORED_PRODUCTS = "SP", "Sponsored Products"
    SPONSORED_BRANDS = "SB", "Sponsored Brands"
    SPONSORED_DISPLAY = "SD", "Sponsored Display"


class EntityState(models.TextChoices):
    ENABLED = "ENABLED", "Enabled"
    PAUSED = "PAUSED", "Paused"
    ARCHIVED = "ARCHIVED", "Archived"
    UNKNOWN = "UNKNOWN", "Unknown"


class MatchType(models.TextChoices):
    BROAD = "BROAD", "Broad"
    PHRASE = "PHRASE", "Phrase"
    EXACT = "EXACT", "Exact"


class Campaign(models.Model):
    profile = models.ForeignKey(
        AdvertisingProfile,
        on_delete=models.PROTECT,
        related_name="campaigns",
    )
    external_campaign_id = models.CharField(max_length=128)
    name = models.CharField(max_length=255)
    ad_product_type = models.CharField(
        max_length=8,
        choices=AdProductType.choices,
        default=AdProductType.SPONSORED_PRODUCTS,
    )
    state = models.CharField(
        max_length=16,
        choices=EntityState.choices,
        default=EntityState.UNKNOWN,
    )
    daily_budget = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
    )
    target_acos = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
    )
    currency_code = models.CharField(max_length=3)
    source_batch = models.ForeignKey(
        "reports.ImportBatch",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="campaigns",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ads_campaign"
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "external_campaign_id"],
                name="ads_campaign_profile_external_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["profile", "state"],
                name="ads_campaign_profile_state_idx",
            )
        ]


class AdGroup(models.Model):
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.PROTECT,
        related_name="ad_groups",
    )
    external_ad_group_id = models.CharField(max_length=128)
    name = models.CharField(max_length=255)
    state = models.CharField(
        max_length=16,
        choices=EntityState.choices,
        default=EntityState.UNKNOWN,
    )
    default_bid = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
    )
    source_batch = models.ForeignKey(
        "reports.ImportBatch",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ad_groups",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ads_ad_group"
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "external_ad_group_id"],
                name="ads_ad_group_campaign_external_uniq",
            )
        ]


class Ad(models.Model):
    ad_group = models.ForeignKey(
        AdGroup,
        on_delete=models.PROTECT,
        related_name="ads",
    )
    listing = models.ForeignKey(
        ProductListing,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ads",
    )
    external_ad_id = models.CharField(max_length=128)
    state = models.CharField(
        max_length=16,
        choices=EntityState.choices,
        default=EntityState.UNKNOWN,
    )
    source_batch = models.ForeignKey(
        "reports.ImportBatch",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ads",
    )

    class Meta:
        db_table = "ads_ad"
        constraints = [
            models.UniqueConstraint(
                fields=["ad_group", "external_ad_id"],
                name="ads_ad_group_external_uniq",
            )
        ]


class Keyword(models.Model):
    ad_group = models.ForeignKey(
        AdGroup,
        on_delete=models.PROTECT,
        related_name="keywords",
    )
    external_keyword_id = models.CharField(max_length=128)
    keyword_text = models.CharField(max_length=500)
    match_type = models.CharField(max_length=16, choices=MatchType.choices)
    is_negative = models.BooleanField(default=False)
    state = models.CharField(
        max_length=16,
        choices=EntityState.choices,
        default=EntityState.UNKNOWN,
    )
    bid = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
    )
    source_batch = models.ForeignKey(
        "reports.ImportBatch",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="keywords",
    )

    class Meta:
        db_table = "ads_keyword"
        constraints = [
            models.UniqueConstraint(
                fields=["ad_group", "external_keyword_id"],
                name="ads_keyword_ad_group_external_uniq",
            )
        ]


class ProductTarget(models.Model):
    ad_group = models.ForeignKey(
        AdGroup,
        on_delete=models.PROTECT,
        related_name="product_targets",
    )
    external_target_id = models.CharField(max_length=128)
    expression = models.CharField(max_length=1000)
    is_negative = models.BooleanField(default=False)
    state = models.CharField(
        max_length=16,
        choices=EntityState.choices,
        default=EntityState.UNKNOWN,
    )
    bid = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
    )
    source_batch = models.ForeignKey(
        "reports.ImportBatch",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="product_targets",
    )

    class Meta:
        db_table = "ads_product_target"
        constraints = [
            models.UniqueConstraint(
                fields=["ad_group", "external_target_id"],
                name="ads_target_ad_group_external_uniq",
            )
        ]


class SearchTerm(models.Model):
    profile = models.ForeignKey(
        AdvertisingProfile,
        on_delete=models.PROTECT,
        related_name="search_terms",
    )
    normalized_text = models.CharField(max_length=1000)
    text_hash = models.CharField(max_length=64)
    display_text = models.CharField(max_length=1000)

    class Meta:
        db_table = "ads_search_term"
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "text_hash"],
                name="ads_search_term_profile_hash_uniq",
            )
        ]
