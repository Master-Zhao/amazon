import uuid

from django.db import models

from apps.advertising.models import Campaign, Keyword, ProductTarget, SearchTerm
from apps.reports.models import ImportBatch
from apps.stores.models import AdvertisingProfile
from apps.tenants.models import Tenant


class MetricMixin(models.Model):
    business_date = models.DateField()
    impressions = models.PositiveBigIntegerField(default=0)
    clicks = models.PositiveBigIntegerField(default=0)
    spend = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    orders = models.PositiveIntegerField(default=0)
    sales = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    ctr = models.DecimalField(max_digits=16, decimal_places=8, null=True)
    cpc = models.DecimalField(max_digits=16, decimal_places=8, null=True)
    cvr = models.DecimalField(max_digits=16, decimal_places=8, null=True)
    acos = models.DecimalField(max_digits=16, decimal_places=8, null=True)
    roas = models.DecimalField(max_digits=16, decimal_places=8, null=True)
    invalid_reasons = models.JSONField(default=dict)
    currency = models.CharField(max_length=3)
    source_batch = models.ForeignKey(ImportBatch, on_delete=models.PROTECT)

    class Meta:
        abstract = True


class CampaignDailyMetric(MetricMixin):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="daily_metrics")
    budget_snapshot = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    state_snapshot = models.CharField(max_length=16)

    class Meta:
        db_table = "analytics_campaign_daily_metric"
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "business_date"],
                name="analytics_campaign_date_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["campaign", "business_date"],
                name="analytics_campaign_date_idx",
            )
        ]


class TargetingDailyMetric(MetricMixin):
    profile = models.ForeignKey(AdvertisingProfile, on_delete=models.CASCADE)
    keyword = models.ForeignKey(Keyword, null=True, on_delete=models.CASCADE)
    product_target = models.ForeignKey(ProductTarget, null=True, on_delete=models.CASCADE)
    targeting_type = models.CharField(max_length=16)
    bid_snapshot = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    state_snapshot = models.CharField(max_length=16)

    class Meta:
        db_table = "analytics_targeting_daily_metric"
        constraints = [
            models.UniqueConstraint(
                fields=["keyword", "business_date"],
                name="analytics_keyword_date_uniq",
            ),
            models.UniqueConstraint(
                fields=["product_target", "business_date"],
                name="analytics_target_date_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["profile", "business_date"],
                name="analytics_tgt_prof_date_idx",
            )
        ]


class SearchTermDailyMetric(MetricMixin):
    search_term = models.ForeignKey(
        SearchTerm, on_delete=models.CASCADE, related_name="daily_metrics"
    )

    class Meta:
        db_table = "analytics_search_term_daily_metric"
        constraints = [
            models.UniqueConstraint(
                fields=["search_term", "business_date"],
                name="analytics_searchterm_date_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["business_date"], name="analytics_searchterm_date_idx"
            )
        ]


class RuleScope(models.TextChoices):
    SYSTEM = "SYSTEM", "System"
    TENANT = "TENANT", "Tenant"
    PROFILE = "PROFILE", "Profile"
    CAMPAIGN = "CAMPAIGN", "Campaign"


class RiskLevel(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical (reserved)"


class AnomalyRuleVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64)
    scope = models.CharField(max_length=16, choices=RuleScope.choices)
    tenant = models.ForeignKey(Tenant, null=True, on_delete=models.CASCADE)
    profile = models.ForeignKey(AdvertisingProfile, null=True, on_delete=models.CASCADE)
    campaign = models.ForeignKey(Campaign, null=True, on_delete=models.CASCADE)
    version = models.PositiveIntegerField()
    thresholds = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analytics_anomaly_rule_version"
        constraints = [
            models.UniqueConstraint(
                fields=["code", "scope", "tenant", "profile", "campaign", "version"],
                name="analytics_rule_scope_version_uniq",
            )
        ]


class AnomalyRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    metric = models.ForeignKey(
        CampaignDailyMetric, on_delete=models.CASCADE, related_name="anomalies"
    )
    rule_version = models.ForeignKey(AnomalyRuleVersion, on_delete=models.PROTECT)
    status = models.CharField(max_length=32)
    risk_level = models.CharField(max_length=16, choices=RiskLevel.choices)
    evidence = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analytics_anomaly_record"
        constraints = [
            models.UniqueConstraint(
                fields=["metric", "rule_version"],
                name="analytics_anomaly_metric_rule_uniq",
            )
        ]
