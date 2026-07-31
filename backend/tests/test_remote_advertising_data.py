from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.stores.models import (
    AdvertisingProfile,
    AmazonStore,
    Marketplace,
    StoreMarketplace,
)
from apps.tenants.models import (
    MembershipRole,
    Tenant,
    TenantMembership,
    TenantType,
)
from config.db_routers import ReadOnlyRemoteDatabaseRouter
from integrations.advertising_data.remote_databases import RemoteCampaignMetric

pytestmark = pytest.mark.django_db


def build_owner_scope(*, email: str, external_profile_id: str):
    user = User.objects.create_user(
        username=email.split("@")[0],
        email=email,
        password="test-only-password",
    )
    tenant = Tenant.objects.create(name=email, tenant_type=TenantType.TEAM)
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        membership_role=MembershipRole.OWNER,
    )
    marketplace = Marketplace.objects.create(
        code=f"M{tenant.pk}",
        name="Remote fixture marketplace",
        currency_code="USD",
        timezone="UTC",
    )
    store = AmazonStore.objects.create(
        tenant=tenant,
        name="Remote fixture store",
        external_store_id=f"store-{tenant.pk}",
    )
    store_marketplace = StoreMarketplace.objects.create(
        store=store,
        marketplace=marketplace,
    )
    profile = AdvertisingProfile.objects.create(
        store_marketplace=store_marketplace,
        external_profile_id=external_profile_id,
        name="Remote fixture profile",
        currency_code="USD",
        timezone="UTC",
    )
    return user, tenant, profile


def remote_metric() -> RemoteCampaignMetric:
    return RemoteCampaignMetric(
        report_date=date(2026, 7, 29),
        external_campaign_id="campaign-100",
        campaign_name="Remote Campaign",
        impressions=1000,
        clicks=50,
        spend=Decimal("75.00"),
        orders=10,
        sales=Decimal("300.00"),
        daily_budget=Decimal("100.00"),
        state="enabled",
        scm_matched=True,
    )


def test_remote_router_never_allows_migrations_on_source_databases():
    router = ReadOnlyRemoteDatabaseRouter()

    assert router.allow_migrate("scm_remote", "analytics") is False
    assert router.allow_migrate("ads_analysis_remote", "analytics") is False
    assert router.allow_migrate("default", "analytics") is None


def test_remote_router_rejects_cross_database_relations():
    router = ReadOnlyRemoteDatabaseRouter()

    class ObjectState:
        def __init__(self, database):
            self._state = type("State", (), {"db": database})()

    assert (
        router.allow_relation(ObjectState("default"), ObjectState("scm_remote"))
        is False
    )
    assert router.allow_relation(ObjectState("default"), ObjectState("default")) is None


def test_remote_campaign_api_enforces_scope_and_returns_camel_case():
    user, tenant, profile = build_owner_scope(
        email="remote-owner@example.invalid",
        external_profile_id="REMOTE-PROFILE-1",
    )
    client = APIClient()
    client.force_authenticate(user)

    with (
        override_settings(
            REMOTE_AD_PROFILE_MERCHANT_MAP={
                "REMOTE-PROFILE-1": {
                    "merchantId": 235,
                    "merchantCode": "W0568",
                }
            }
        ),
        patch(
            "integrations.advertising_data.remote_databases."
            "RemoteAdvertisingDataReader.campaign_metrics",
            return_value=[remote_metric()],
        ) as reader,
    ):
        response = client.get(
            f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{profile.pk}/"
            "remote-campaigns"
        )

    assert response.status_code == 200
    assert response.json()["data"] == [
        {
            "id": "remote:2026-07-29:campaign-100",
            "externalCampaignId": "campaign-100",
            "campaignName": "Remote Campaign",
            "reportDate": "2026-07-29",
            "currencyCode": "USD",
            "impressions": 1000,
            "clicks": 50,
            "spend": "75.00",
            "orders": 10,
            "sales": "300.00",
            "dailyBudget": "100.00",
            "state": "enabled",
            "ctr": {"value": "0.05", "reason": None},
            "cpc": {"value": "1.50", "reason": None},
            "cvr": {"value": "0.2", "reason": None},
            "acos": {"value": "0.25", "reason": None},
            "roas": {"value": "4", "reason": None},
            "scmMatched": True,
            "sourceSystem": "REMOTE_MYSQL",
        }
    ]
    reader.assert_called_once_with(
        merchant_id=235,
        merchant_code="W0568",
        start_date=None,
        end_date=None,
    )


def test_remote_campaign_api_hides_cross_tenant_profile():
    user, tenant, _ = build_owner_scope(
        email="scope-owner@example.invalid",
        external_profile_id="REMOTE-PROFILE-2",
    )
    _, _, other_profile = build_owner_scope(
        email="other-owner@example.invalid",
        external_profile_id="REMOTE-PROFILE-3",
    )
    client = APIClient()
    client.force_authenticate(user)

    response = client.get(
        f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{other_profile.pk}/"
        "remote-campaigns"
    )

    assert response.status_code == 404


def test_remote_campaign_api_reports_missing_profile_mapping():
    user, tenant, profile = build_owner_scope(
        email="unmapped-owner@example.invalid",
        external_profile_id="UNMAPPED-PROFILE",
    )
    client = APIClient()
    client.force_authenticate(user)

    with override_settings(REMOTE_AD_PROFILE_MERCHANT_MAP={}):
        response = client.get(
            f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{profile.pk}/"
            "remote-campaigns"
        )

    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_NOT_READY"
    assert (
        response.json()["message"]
        == "当前 Profile 尚未配置远程商户与店铺编码映射"
    )
