from dataclasses import replace
from datetime import date
from decimal import Decimal
from unittest.mock import call, patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
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
from integrations.advertising_data.remote_databases import (
    RemoteCampaignMetric,
    RemoteCampaignDailyTotals,
    RemoteCampaignOverviewMetric,
    RemoteCampaignOverviewPage,
    RemoteCampaignOverviewTotals,
    RemoteCampaignRiskMetric,
)

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


def remote_overview_page() -> RemoteCampaignOverviewPage:
    metric = RemoteCampaignOverviewMetric(
        campaign_key="campaign-100",
        reference_code="SP-DEMO-100",
        campaign_name="Remote Campaign",
        targeting_type="auto",
        state="enabled",
        bidding_strategy="fixed_bids",
        start_date=date(2026, 7, 1),
        end_date=None,
        daily_budget=Decimal("100.00"),
        impressions=1000,
        clicks=50,
        spend=Decimal("75.00"),
        orders=10,
        sales=Decimal("300.00"),
        top_of_search_share=Decimal("0.375"),
        scm_matched=True,
    )
    return RemoteCampaignOverviewPage(
        items=[metric],
        summary=RemoteCampaignOverviewTotals(
            impressions=1000,
            clicks=50,
            spend=Decimal("75.00"),
            orders=10,
            sales=Decimal("300.00"),
            top_of_search_share=Decimal("0.375"),
        ),
        page=1,
        page_size=15,
        total=1,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 30),
        data_through_date=date(2026, 7, 30),
        trend=[
            RemoteCampaignDailyTotals(
                report_date=date(2026, 7, 30),
                impressions=1000,
                clicks=50,
                spend=Decimal("75.00"),
                orders=10,
                sales=Decimal("300.00"),
            )
        ],
        risk_metrics=[
            RemoteCampaignRiskMetric(
                campaign_key="campaign-100",
                impressions=1000,
                clicks=50,
                spend=Decimal("75.00"),
                orders=10,
                sales=Decimal("300.00"),
            )
        ],
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


def test_campaign_overview_api_returns_paginated_remote_contract():
    user, tenant, profile = build_owner_scope(
        email="campaign-overview@example.invalid",
        external_profile_id="REMOTE-PROFILE-OVERVIEW",
    )
    client = APIClient()
    client.force_authenticate(user)

    with (
        override_settings(
            REMOTE_AD_PROFILE_MERCHANT_MAP={
                "REMOTE-PROFILE-OVERVIEW": {
                    "merchantId": 235,
                    "merchantCode": "W0568",
                }
            }
        ),
        patch(
            "integrations.advertising_data.remote_databases."
            "RemoteAdvertisingDataReader.campaign_overview",
            return_value=remote_overview_page(),
        ) as reader,
    ):
        response = client.get(
            f"/api/v1/advertising/tenants/{tenant.pk}/profiles/{profile.pk}/"
            "campaigns",
            {
                "enabled": "true",
                "status": "enabled",
                "targetingType": "AUTO",
                "search": "Remote",
                "metricFilters": "impressions:gte:100;acos:between:0.1:0.5",
                "ordering": "-spend",
                "page": 1,
                "pageSize": 15,
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["pagination"] == {
        "page": 1,
        "pageSize": 15,
        "total": 1,
        "totalPages": 1,
    }
    assert payload["items"][0]["name"] == "Remote Campaign"
    assert payload["items"][0]["campaignKey"].startswith("cmp_")
    assert "W0568" not in payload["items"][0]["campaignKey"]
    assert payload["items"][0]["metrics"] == {
        "impressions": 1000,
        "topOfSearchShare": "0.375",
        "spend": {"amount": "75.00", "currencyCode": "USD"},
        "sales": {"amount": "300.00", "currencyCode": "USD"},
        "clicks": 50,
        "ctr": "0.05",
        "totalCost": {"amount": "75.00", "currencyCode": "USD"},
        "orders": 10,
        "cpc": {"amount": "1.50", "currencyCode": "USD"},
        "acos": "0.25",
        "cvr": "0.2",
    }
    assert payload["dashboard"]["trend"][0]["date"] == "2026-07-30"
    assert payload["dashboard"]["evaluatedCampaigns"] == 1
    assert sum(item["count"] for item in payload["dashboard"]["riskLevels"]) == 1
    assert payload["meta"]["attributionSemantics"] == "REMOTE_FIELDS_UNVERIFIED"
    reader.assert_called_once_with(
        merchant_id=235,
        merchant_code="W0568",
        start_date=None,
        end_date=None,
        enabled=True,
        statuses=("enabled",),
        targeting_type="AUTO",
        search="Remote",
        metric_filters=(
            {
                "field": "impressions",
                "operator": "gte",
                "value": Decimal("100"),
            },
            {
                "field": "acos",
                "operator": "between",
                "value": Decimal("0.1"),
                "value2": Decimal("0.5"),
            },
        ),
        ordering="-spend",
        page=1,
        page_size=15,
        include_summary=True,
        require_metrics=True,
    )


def test_campaign_overview_api_does_not_filter_enabled_when_query_omits_it():
    user, tenant, profile = build_owner_scope(
        email="campaign-overview-all@example.invalid",
        external_profile_id="REMOTE-PROFILE-OVERVIEW-ALL",
    )
    client = APIClient()
    client.force_authenticate(user)

    with (
        override_settings(
            REMOTE_AD_PROFILE_MERCHANT_MAP={
                "REMOTE-PROFILE-OVERVIEW-ALL": {
                    "merchantId": 235,
                    "merchantCode": "W0568",
                }
            }
        ),
        patch(
            "integrations.advertising_data.remote_databases."
            "RemoteAdvertisingDataReader.campaign_overview",
            return_value=remote_overview_page(),
        ) as reader,
    ):
        response = client.get(
            f"/api/v1/advertising/tenants/{tenant.pk}/profiles/{profile.pk}/"
            "campaigns",
            {"page": 1},
        )

    assert response.status_code == 200
    assert reader.call_args.kwargs["enabled"] is None
    assert reader.call_args.kwargs["statuses"] == ()
    assert reader.call_args.kwargs["require_metrics"] is False


def test_campaign_overview_api_requires_metrics_when_date_range_is_explicit():
    user, tenant, profile = build_owner_scope(
        email="campaign-overview-dated@example.invalid",
        external_profile_id="REMOTE-PROFILE-OVERVIEW-DATED",
    )
    client = APIClient()
    client.force_authenticate(user)

    with (
        override_settings(
            REMOTE_AD_PROFILE_MERCHANT_MAP={
                "REMOTE-PROFILE-OVERVIEW-DATED": {
                    "merchantId": 235,
                    "merchantCode": "W0568",
                }
            }
        ),
        patch(
            "integrations.advertising_data.remote_databases."
            "RemoteAdvertisingDataReader.campaign_overview",
            return_value=remote_overview_page(),
        ) as reader,
    ):
        response = client.get(
            f"/api/v1/advertising/tenants/{tenant.pk}/profiles/{profile.pk}/"
            "campaigns",
            {
                "startDate": "2026-07-01",
                "endDate": "2026-07-30",
                "page": 1,
            },
        )

    assert response.status_code == 200
    assert reader.call_args.kwargs["require_metrics"] is True


def test_campaign_overview_api_rejects_invalid_date_range_before_remote_query():
    user, tenant, profile = build_owner_scope(
        email="campaign-date-range@example.invalid",
        external_profile_id="REMOTE-PROFILE-DATES",
    )
    client = APIClient()
    client.force_authenticate(user)

    with patch(
        "integrations.advertising_data.remote_databases."
        "RemoteAdvertisingDataReader.campaign_overview"
    ) as reader:
        response = client.get(
            f"/api/v1/advertising/tenants/{tenant.pk}/profiles/{profile.pk}/"
            "campaigns",
            {
                "startDate": "2026-01-01",
                "endDate": "2026-04-02",
                "page": 1,
            },
        )

    assert response.status_code == 400
    reader.assert_not_called()


def test_campaign_overview_api_rejects_invalid_metric_filter_before_remote_query():
    user, tenant, profile = build_owner_scope(
        email="campaign-metric-filter@example.invalid",
        external_profile_id="REMOTE-PROFILE-METRIC-FILTER",
    )
    client = APIClient()
    client.force_authenticate(user)

    with patch(
        "integrations.advertising_data.remote_databases."
        "RemoteAdvertisingDataReader.campaign_overview"
    ) as reader:
        response = client.get(
            f"/api/v1/advertising/tenants/{tenant.pk}/profiles/{profile.pk}/"
            "campaigns",
            {"page": 1, "metricFilters": "spend:between:200:100"},
        )

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    reader.assert_not_called()


def test_campaign_detail_api_resolves_signed_key_without_exposing_remote_key():
    user, tenant, profile = build_owner_scope(
        email="campaign-detail@example.invalid",
        external_profile_id="REMOTE-PROFILE-DETAIL",
    )
    client = APIClient()
    client.force_authenticate(user)

    mapping = {
        "REMOTE-PROFILE-DETAIL": {
            "merchantId": 235,
            "merchantCode": "W0568",
        }
    }
    with (
        override_settings(REMOTE_AD_PROFILE_MERCHANT_MAP=mapping),
        patch(
            "integrations.advertising_data.remote_databases."
            "RemoteAdvertisingDataReader.campaign_overview",
            return_value=remote_overview_page(),
        ),
    ):
        list_response = client.get(
            f"/api/v1/advertising/tenants/{tenant.pk}/profiles/{profile.pk}/"
            "campaigns",
            {"page": 1},
        )
    campaign_key = list_response.json()["data"]["items"][0]["campaignKey"]

    with (
        override_settings(REMOTE_AD_PROFILE_MERCHANT_MAP=mapping),
        patch(
            "integrations.advertising_data.remote_databases."
            "RemoteAdvertisingDataReader.campaign_detail",
            return_value=remote_overview_page(),
        ) as reader,
    ):
        response = client.get(
            f"/api/v1/advertising/tenants/{tenant.pk}/profiles/{profile.pk}/"
            f"campaigns/{campaign_key}",
            {"startDate": "2026-07-01", "endDate": "2026-07-30"},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["item"]["name"] == "Remote Campaign"
    assert payload["item"]["campaignKey"] == campaign_key
    assert payload["trend"][0]["date"] == "2026-07-30"
    reader.assert_called_once_with(
        merchant_id=235,
        merchant_code="W0568",
        campaign_key="campaign-100",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 30),
    )


def test_campaign_enabled_update_api_writes_remote_scm_state_and_returns_item():
    user, tenant, profile = build_owner_scope(
        email="campaign-enabled-update@example.invalid",
        external_profile_id="REMOTE-PROFILE-ENABLED-UPDATE",
    )
    client = APIClient()
    client.force_authenticate(user)
    mapping = {
        "REMOTE-PROFILE-ENABLED-UPDATE": {
            "merchantId": 235,
            "merchantCode": "W0568",
        }
    }
    with (
        override_settings(REMOTE_AD_PROFILE_MERCHANT_MAP=mapping),
        patch(
            "integrations.advertising_data.remote_databases."
            "RemoteAdvertisingDataReader.campaign_overview",
            return_value=remote_overview_page(),
        ),
    ):
        list_response = client.get(
            f"/api/v1/advertising/tenants/{tenant.pk}/profiles/{profile.pk}/"
            "campaigns",
            {"page": 1},
        )
    campaign_key = list_response.json()["data"]["items"][0]["campaignKey"]
    page = remote_overview_page()
    updated_page = replace(
        page,
        items=[replace(page.items[0], state="paused")],
    )

    with (
        override_settings(REMOTE_AD_PROFILE_MERCHANT_MAP=mapping),
        patch(
            "integrations.advertising_data.remote_databases."
            "RemoteAdvertisingDataReader.update_campaign_enabled",
            return_value=True,
        ) as updater,
        patch(
            "integrations.advertising_data.remote_databases."
            "RemoteAdvertisingDataReader.campaign_detail",
            return_value=updated_page,
        ) as detail_reader,
    ):
        response = client.patch(
            f"/api/v1/advertising/tenants/{tenant.pk}/profiles/{profile.pk}/"
            f"campaigns/{campaign_key}/enabled",
            {
                "enabled": False,
                "startDate": "2026-07-01",
                "endDate": "2026-07-30",
            },
            format="json",
        )

    assert response.status_code == 200
    assert response.json()["data"]["item"]["enabled"] is False
    assert response.json()["data"]["item"]["status"] == "PAUSED"
    updater.assert_called_once_with(
        merchant_id=235,
        merchant_code="W0568",
        campaign_key="campaign-100",
        enabled=False,
        campaign_name="Remote Campaign",
        targeting_type="auto",
        daily_budget=Decimal("100.00"),
        bidding_strategy="fixed_bids",
        start_date=date(2026, 7, 1),
        end_date=None,
        actor_id=user.pk,
        actor_name=user.email,
    )
    detail_reader.assert_has_calls(
        [
            call(
                merchant_id=235,
                merchant_code="W0568",
                campaign_key="campaign-100",
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 30),
            ),
            call(
                merchant_id=235,
                merchant_code="W0568",
                campaign_key="campaign-100",
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 30),
            ),
        ]
    )
    log = AuditLog.objects.get(event="campaign.enabled_updated")
    assert log.object_id == "campaign-100"
    assert log.after_data == {"enabled": False}


def test_campaign_create_api_writes_remote_scm_and_returns_created_item():
    user, tenant, profile = build_owner_scope(
        email="campaign-create@example.invalid",
        external_profile_id="REMOTE-PROFILE-CREATE",
    )
    client = APIClient()
    client.force_authenticate(user)
    mapping = {
        "REMOTE-PROFILE-CREATE": {
            "merchantId": 235,
            "merchantCode": "W0568",
        }
    }
    page = remote_overview_page()
    created_page = replace(
        page,
        items=[
            replace(
                page.items[0],
                campaign_key="CODX-W0568-test",
                reference_code="CODX-W0568-test",
                campaign_name="新建远程活动",
                targeting_type="manual",
                state="paused",
                daily_budget=Decimal("25.50"),
                scm_matched=True,
                has_metrics=False,
                impressions=None,
                clicks=None,
                spend=None,
                sales=None,
                orders=None,
                top_of_search_share=None,
            )
        ],
    )

    with (
        override_settings(REMOTE_AD_PROFILE_MERCHANT_MAP=mapping),
        patch(
            "integrations.advertising_data.remote_databases."
            "RemoteAdvertisingDataReader.create_campaign",
            return_value="CODX-W0568-test",
        ) as creator,
        patch(
            "integrations.advertising_data.remote_databases."
            "RemoteAdvertisingDataReader.campaign_detail",
            return_value=created_page,
        ) as detail_reader,
    ):
        response = client.post(
            f"/api/v1/advertising/tenants/{tenant.pk}/profiles/{profile.pk}/"
            "campaigns",
            {
                "name": "新建远程活动",
                "targetingType": "MANUAL",
                "dailyBudget": "25.50",
                "biddingStrategy": "down_only",
                "startDate": "2026-08-05",
                "enabled": False,
            },
            format="json",
        )

    assert response.status_code == 201
    payload = response.json()["data"]["item"]
    assert payload["name"] == "新建远程活动"
    assert payload["enabled"] is False
    assert payload["dailyBudget"] == {"amount": "25.50", "currencyCode": "USD"}
    creator.assert_called_once_with(
        merchant_id=235,
        merchant_code="W0568",
        name="新建远程活动",
        targeting_type="MANUAL",
        daily_budget=Decimal("25.50"),
        bidding_strategy="down_only",
        start_date=date(2026, 8, 5),
        end_date=None,
        enabled=False,
        actor_id=user.pk,
        actor_name=user.email,
    )
    detail_reader.assert_called_once_with(
        merchant_id=235,
        merchant_code="W0568",
        campaign_key="CODX-W0568-test",
        start_date=date(2026, 8, 5),
        end_date=date(2026, 8, 5),
    )
    log = AuditLog.objects.get(event="campaign.created")
    assert log.object_id == "CODX-W0568-test"
    assert log.after_data["name"] == "新建远程活动"


def test_campaign_detail_api_rejects_key_from_another_remote_scope():
    user, tenant, profile = build_owner_scope(
        email="campaign-detail-scope@example.invalid",
        external_profile_id="REMOTE-PROFILE-DETAIL-SCOPE",
    )
    client = APIClient()
    client.force_authenticate(user)
    mapping = {
        "REMOTE-PROFILE-DETAIL-SCOPE": {
            "merchantId": 235,
            "merchantCode": "W0568",
        }
    }
    with (
        override_settings(REMOTE_AD_PROFILE_MERCHANT_MAP=mapping),
        patch(
            "integrations.advertising_data.remote_databases."
            "RemoteAdvertisingDataReader.campaign_overview",
            return_value=remote_overview_page(),
        ),
    ):
        list_response = client.get(
            f"/api/v1/advertising/tenants/{tenant.pk}/profiles/{profile.pk}/"
            "campaigns",
            {"page": 1},
        )
    campaign_key = list_response.json()["data"]["items"][0]["campaignKey"]

    with override_settings(
        REMOTE_AD_PROFILE_MERCHANT_MAP={
            "REMOTE-PROFILE-DETAIL-SCOPE": {
                "merchantId": 999,
                "merchantCode": "OTHER",
            }
        }
    ):
        response = client.get(
            f"/api/v1/advertising/tenants/{tenant.pk}/profiles/{profile.pk}/"
            f"campaigns/{campaign_key}"
        )

    assert response.status_code == 404


def test_campaign_export_is_utf8_bom_formula_safe_and_audited():
    user, tenant, profile = build_owner_scope(
        email="campaign-export@example.invalid",
        external_profile_id="REMOTE-PROFILE-EXPORT",
    )
    client = APIClient()
    client.force_authenticate(user)
    page = remote_overview_page()
    page = replace(
        page,
        items=[replace(page.items[0], campaign_name="=unsafe campaign")],
    )

    with (
        override_settings(
            REMOTE_AD_PROFILE_MERCHANT_MAP={
                "REMOTE-PROFILE-EXPORT": {
                    "merchantId": 235,
                    "merchantCode": "W0568",
                }
            }
        ),
        patch(
            "integrations.advertising_data.remote_databases."
            "RemoteAdvertisingDataReader.campaign_overview",
            return_value=page,
        ),
    ):
        response = client.get(
            f"/api/v1/advertising/tenants/{tenant.pk}/profiles/{profile.pk}/"
            "campaigns/export",
            {"enabled": "true", "ordering": "-spend"},
        )

    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"
    assert response["Content-Type"].startswith("text/csv")
    assert response.content.startswith(b"\xef\xbb\xbf")
    assert "'=unsafe campaign" in response.content.decode("utf-8-sig")
    log = AuditLog.objects.get(event="campaign.exported")
    assert log.tenant_id == tenant.pk
    assert log.actor_id == user.pk
    assert log.object_id == str(profile.pk)
    assert log.metadata == {"row_count": 1, "source": "REMOTE_MYSQL"}
