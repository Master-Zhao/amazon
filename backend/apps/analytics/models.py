from django.db import models

from apps.advertising.models import (
    AdGroup,
    Campaign,
    EntityState,
    Keyword,
    ProductTarget,
    SearchTerm,
)
from apps.core.models import AppendOnlyModel
from apps.reports.models import ImportBatch
from apps.stores.models import AdvertisingProfile
from apps.tenants.models import Tenant


class AnomalyRuleCode(models.TextChoices):
    HIGH_ACOS = "HIGH_ACOS", "High ACOS"
    HIGH_SPEND_NO_ORDERS = "HIGH_SPEND_NO_ORDERS", "High spend with no orders"
    HIGH_CLICKS_LOW_CONVERSION = (
        "HIGH_CLICKS_LOW_CONVERSION",
        "High clicks with low conversion",
    )
    BUDGET_EARLY_EXHAUSTION = (
        "BUDGET_EARLY_EXHAUSTION",
        "Budget exhausted early",
    )
    LOW_IMPRESSIONS = "LOW_IMPRESSIONS", "Low impressions"
    LOW_CLICKS = "LOW_CLICKS", "Low clicks"


class AnomalyStatus(models.TextChoices):
    NORMAL = "NORMAL", "Normal"
    ANOMALY = "ANOMALY", "Anomaly"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA", "Insufficient data"


class RiskLevel(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class TargetingEntityType(models.TextChoices):
    KEYWORD = "KEYWORD", "Keyword"
    PRODUCT_TARGET = "PRODUCT_TARGET", "Product Target"


class CampaignDailyMetric(models.Model):
    profile = models.ForeignKey(
        AdvertisingProfile,
        on_delete=models.PROTECT,
        related_name="campaign_daily_metrics",
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.PROTECT,
        related_name="daily_metrics",
    )
    report_date = models.DateField()
    currency_code = models.CharField(max_length=3)
    impressions = models.PositiveBigIntegerField()
    clicks = models.PositiveBigIntegerField()
    spend = models.DecimalField(max_digits=20, decimal_places=4)
    orders = models.PositiveBigIntegerField()
    sales = models.DecimalField(max_digits=20, decimal_places=4)
    calculation_reasons = models.JSONField(default=dict)
    daily_budget_snapshot = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
    )
    snapshot_hour_local = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    state_snapshot = models.CharField(
        max_length=16,
        choices=EntityState.choices,
    )
    source_batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.PROTECT,
        related_name="campaign_daily_metrics",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_campaign_daily_metric"
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "campaign", "report_date"],
                name="analytics_campaign_daily_natural_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["profile", "report_date"],
                name="anly_camp_profile_date_idx",
            ),
            models.Index(
                fields=["campaign", "report_date"],
                name="anly_camp_entity_date_idx",
            ),
        ]


class CampaignMetricRevision(AppendOnlyModel):
    metric = models.ForeignKey(
        CampaignDailyMetric,
        on_delete=models.PROTECT,
        related_name="revisions",
    )
    source_batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.PROTECT,
        related_name="campaign_metric_revisions",
    )
    previous_values = models.JSONField(default=dict)
    current_values = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analytics_campaign_metric_revision"
        constraints = [
            models.UniqueConstraint(
                fields=["metric", "source_batch"],
                name="analytics_metric_revision_batch_uniq",
            )
        ]


class TargetingDailyMetric(models.Model):
    profile = models.ForeignKey(
        AdvertisingProfile,
        on_delete=models.PROTECT,
        related_name="targeting_daily_metrics",
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.PROTECT,
        related_name="targeting_daily_metrics",
    )
    ad_group = models.ForeignKey(
        AdGroup,
        on_delete=models.PROTECT,
        related_name="targeting_daily_metrics",
    )
    target_type = models.CharField(
        max_length=32,
        choices=TargetingEntityType.choices,
    )
    target_key = models.CharField(max_length=160)
    keyword = models.ForeignKey(
        Keyword,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="daily_metrics",
    )
    product_target = models.ForeignKey(
        ProductTarget,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="daily_metrics",
    )
    report_date = models.DateField()
    currency_code = models.CharField(max_length=3)
    impressions = models.PositiveBigIntegerField()
    clicks = models.PositiveBigIntegerField()
    spend = models.DecimalField(max_digits=20, decimal_places=4)
    orders = models.PositiveBigIntegerField()
    sales = models.DecimalField(max_digits=20, decimal_places=4)
    calculation_reasons = models.JSONField(default=dict)
    bid_snapshot = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
    )
    state_snapshot = models.CharField(
        max_length=16,
        choices=EntityState.choices,
    )
    source_batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.PROTECT,
        related_name="targeting_daily_metrics",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_targeting_daily_metric"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        target_type=TargetingEntityType.KEYWORD,
                        keyword__isnull=False,
                        product_target__isnull=True,
                    )
                    | models.Q(
                        target_type=TargetingEntityType.PRODUCT_TARGET,
                        keyword__isnull=True,
                        product_target__isnull=False,
                    )
                ),
                name="anly_target_metric_entity_check",
            ),
            models.UniqueConstraint(
                fields=["profile", "target_key", "report_date"],
                name="anly_target_entity_daily_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["profile", "report_date", "target_type"],
                name="anly_target_profile_date_idx",
            )
        ]


class TargetingMetricRevision(AppendOnlyModel):
    metric = models.ForeignKey(
        TargetingDailyMetric,
        on_delete=models.PROTECT,
        related_name="revisions",
    )
    source_batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.PROTECT,
        related_name="targeting_metric_revisions",
    )
    previous_values = models.JSONField(default=dict)
    current_values = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analytics_targeting_metric_revision"
        constraints = [
            models.UniqueConstraint(
                fields=["metric", "source_batch"],
                name="anly_target_revision_batch_uniq",
            )
        ]


class SearchTermDailyMetric(models.Model):
    profile = models.ForeignKey(
        AdvertisingProfile,
        on_delete=models.PROTECT,
        related_name="search_term_daily_metrics",
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.PROTECT,
        related_name="search_term_daily_metrics",
    )
    ad_group = models.ForeignKey(
        AdGroup,
        on_delete=models.PROTECT,
        related_name="search_term_daily_metrics",
    )
    search_term = models.ForeignKey(
        SearchTerm,
        on_delete=models.PROTECT,
        related_name="daily_metrics",
    )
    report_date = models.DateField()
    targeting_expression_hash = models.CharField(max_length=64)
    targeting_expression_snapshot = models.CharField(max_length=1000)
    currency_code = models.CharField(max_length=3)
    impressions = models.PositiveBigIntegerField()
    clicks = models.PositiveBigIntegerField()
    spend = models.DecimalField(max_digits=20, decimal_places=4)
    orders = models.PositiveBigIntegerField()
    sales = models.DecimalField(max_digits=20, decimal_places=4)
    calculation_reasons = models.JSONField(default=dict)
    source_batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.PROTECT,
        related_name="search_term_daily_metrics",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_search_term_daily_metric"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "profile",
                    "campaign",
                    "ad_group",
                    "search_term",
                    "report_date",
                    "targeting_expression_hash",
                ],
                name="anly_search_term_daily_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["profile", "report_date"],
                name="anly_search_profile_date_idx",
            ),
            models.Index(
                fields=["search_term", "report_date"],
                name="anly_search_entity_date_idx",
            ),
        ]


class SearchTermMetricRevision(AppendOnlyModel):
    metric = models.ForeignKey(
        SearchTermDailyMetric,
        on_delete=models.PROTECT,
        related_name="revisions",
    )
    source_batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.PROTECT,
        related_name="search_term_metric_revisions",
    )
    previous_values = models.JSONField(default=dict)
    current_values = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analytics_search_term_metric_revision"
        constraints = [
            models.UniqueConstraint(
                fields=["metric", "source_batch"],
                name="anly_search_revision_batch_uniq",
            )
        ]


class AnomalyRuleVersion(models.Model):
    code = models.CharField(max_length=64, choices=AnomalyRuleCode.choices)
    version = models.PositiveIntegerField()
    scope_key = models.CharField(max_length=160, default="SYSTEM")
    tenant = models.ForeignKey(
        Tenant,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="anomaly_rule_versions",
    )
    profile = models.ForeignKey(
        AdvertisingProfile,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="anomaly_rule_versions",
    )
    campaign = models.ForeignKey(
        Campaign,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="anomaly_rule_versions",
    )
    configuration = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analytics_anomaly_rule_version"
        constraints = [
            models.UniqueConstraint(
                fields=["code", "version", "scope_key"],
                name="analytics_rule_scope_version_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["code", "is_active"],
                name="analytics_rule_code_active_idx",
            )
        ]


class AnomalyRecord(AppendOnlyModel):
    metric = models.ForeignKey(
        CampaignDailyMetric,
        on_delete=models.PROTECT,
        related_name="anomaly_records",
    )
    rule_version = models.ForeignKey(
        AnomalyRuleVersion,
        on_delete=models.PROTECT,
        related_name="records",
    )
    source_batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.PROTECT,
        related_name="anomaly_records",
    )
    status = models.CharField(max_length=32, choices=AnomalyStatus.choices)
    risk_level = models.CharField(
        max_length=16,
        choices=RiskLevel.choices,
        null=True,
        blank=True,
    )
    observed_value = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
    )
    threshold_value = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
    )
    reason_code = models.CharField(max_length=96, blank=True)
    explanation = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analytics_anomaly_record"
        constraints = [
            models.UniqueConstraint(
                fields=["metric", "rule_version", "source_batch"],
                name="analytics_anomaly_metric_rule_batch_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["status", "risk_level", "-created_at"],
                name="anly_anom_status_risk_idx",
            )
        ]
