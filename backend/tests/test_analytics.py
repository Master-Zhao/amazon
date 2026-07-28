from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.advertising.models import Campaign, EntityState
from apps.analytics.calculations import calculate_metrics
from apps.analytics.models import AnomalyRecord, CampaignDailyMetric
from apps.analytics.selectors import dashboard
from apps.analytics.services import target_acos_for, upsert_daily_metric
from apps.reports.models import (
    ImportBatch,
    ImportStatus,
    ImportTask,
    ReportType,
    ReportUpload,
)
from apps.stores.models import (
    AdvertisingProfile,
    AmazonStore,
    Marketplace,
    StoreMarketplace,
)
from apps.tenants.models import MembershipRole, Tenant, TenantMembership, TenantType


@pytest.fixture
def analytics_context(db):
    user = get_user_model().objects.create_user(
        username="analyst", email="analyst@example.invalid", password="password"
    )
    tenant = Tenant.objects.create(
        name="Analytics", tenant_type=TenantType.PERSONAL, target_acos="0.3000"
    )
    TenantMembership.objects.create(
        tenant=tenant, user=user, role=MembershipRole.OWNER
    )
    marketplace = Marketplace.objects.create(
        code="US",
        name="Amazon.com",
        country_code="US",
        currency="USD",
        timezone="America/Los_Angeles",
    )
    store = AmazonStore.objects.create(
        tenant=tenant, name="Store", external_store_id="ANALYTICS-STORE"
    )
    scope = StoreMarketplace.objects.create(
        store=store, marketplace=marketplace, seller_id="SELLER"
    )
    profile = AdvertisingProfile.objects.create(
        store_marketplace=scope,
        external_profile_id="P-1",
        name="Profile",
        currency="USD",
        timezone=marketplace.timezone,
        target_acos="0.2500",
    )
    campaign = Campaign.objects.create(
        profile=profile,
        external_campaign_id="C-1",
        name="Campaign",
        state=EntityState.ENABLED,
        daily_budget="50.00",
        currency="USD",
    )
    upload = ReportUpload.objects.create(
        tenant=tenant,
        profile=profile,
        report_type=ReportType.CAMPAIGN,
        original_name="fixture.csv",
        content_type="text/csv",
        size_bytes=1,
        sha256="a" * 64,
        storage_path="reports/fixture.csv",
        uploaded_by=user,
    )
    task = ImportTask.objects.create(
        upload=upload,
        status=ImportStatus.RUNNING,
        requested_by=user,
        idempotency_key="analytics-test",
    )
    batch = ImportBatch.objects.create(task=task, status=ImportStatus.RUNNING)
    return user, tenant, profile, campaign, batch


def test_deterministic_formulas_and_zero_denominators():
    calculated = calculate_metrics(
        impressions=100, clicks=10, spend="20.00", orders=2, sales="80.00"
    )
    empty = calculate_metrics(
        impressions=0, clicks=0, spend="0", orders=0, sales="0"
    )

    assert calculated["ctr"] == Decimal("0.1")
    assert calculated["cpc"] == Decimal("2")
    assert calculated["cvr"] == Decimal("0.2")
    assert calculated["acos"] == Decimal("0.25")
    assert calculated["roas"] == Decimal("4")
    assert empty["ctr"] is None and empty["acos"] is None and empty["roas"] is None
    assert empty["invalid_reasons"]["acos"] == "NO_SALES"


@pytest.mark.django_db
def test_campaign_metric_preserves_snapshots_and_batch_lineage(analytics_context):
    _, _, profile, campaign, batch = analytics_context
    metric = upsert_daily_metric(
        report_type=ReportType.CAMPAIGN,
        profile=profile,
        batch=batch,
        row={
            "date": "2026-07-20",
            "impressions": "1000",
            "clicks": "50",
            "spend": "100",
            "orders": "5",
            "sales": "200",
        },
        normalized_object=campaign,
    )
    campaign.daily_budget = Decimal("80")
    campaign.state = EntityState.PAUSED
    campaign.save()

    metric.refresh_from_db()
    assert metric.budget_snapshot == Decimal("50")
    assert metric.state_snapshot == EntityState.ENABLED
    assert metric.source_batch == batch
    assert metric.acos == Decimal("0.5")


@pytest.mark.django_db
def test_target_acos_inheritance_and_anomaly_rule(analytics_context):
    _, tenant, profile, campaign, batch = analytics_context
    assert target_acos_for(campaign) == Decimal("0.2500")
    campaign.target_acos = Decimal("0.2000")
    campaign.save(update_fields=["target_acos"])
    assert target_acos_for(campaign) == Decimal("0.2000")

    metric = upsert_daily_metric(
        report_type=ReportType.CAMPAIGN,
        profile=profile,
        batch=batch,
        row={
            "date": "2026-07-20",
            "impressions": "1000",
            "clicks": "20",
            "spend": "100",
            "orders": "1",
            "sales": "100",
        },
        normalized_object=campaign,
    )
    anomaly = AnomalyRecord.objects.get(metric=metric)
    assert anomaly.status == "ANOMALOUS"
    assert anomaly.risk_level == "HIGH"


@pytest.mark.django_db
def test_dashboard_uses_campaign_fact_only(analytics_context):
    user, tenant, profile, campaign, batch = analytics_context
    upsert_daily_metric(
        report_type=ReportType.CAMPAIGN,
        profile=profile,
        batch=batch,
        row={
            "date": "2026-07-20",
            "impressions": "100",
            "clicks": "10",
            "spend": "20",
            "orders": "2",
            "sales": "80",
        },
        normalized_object=campaign,
    )
    result = dashboard(user, tenant.pk, profile.pk)

    assert result["currency"] == "USD"
    assert result["totals"]["spend"] == Decimal("20")
    assert len(result["series"]) == 1
