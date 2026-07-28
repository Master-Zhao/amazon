from pathlib import Path
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from openpyxl import Workbook

from apps.advertising.models import Campaign, Keyword, ProductTarget, SearchTerm
from apps.reports.models import ImportStatus, ImportTask, ReportType, ReportUpload
from apps.stores.models import (
    AdvertisingProfile,
    AmazonStore,
    Marketplace,
    StoreMarketplace,
)
from apps.tenants.models import MembershipRole, Tenant, TenantMembership, TenantType
from integrations.advertising_data.sources import (
    AmazonAdsApiReportSource,
    FileUploadReportSource,
    ThirdPartyProviderReportSource,
)

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "reports"


@pytest.fixture
def report_context(db):
    user = get_user_model().objects.create_user(
        username="report-owner",
        email="report-owner@example.invalid",
        password="password",
    )
    tenant = Tenant.objects.create(name="Report Tenant", tenant_type=TenantType.PERSONAL)
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
        tenant=tenant, name="Report Store", external_store_id="REPORT-STORE"
    )
    scope = StoreMarketplace.objects.create(
        store=store, marketplace=marketplace, seller_id="REPORT-SELLER"
    )
    profile = AdvertisingProfile.objects.create(
        store_marketplace=scope,
        external_profile_id="DEMO-PROFILE-001",
        name="Report Profile",
        currency="USD",
        timezone=marketplace.timezone,
    )
    client = APIClient()
    client.force_authenticate(user)
    return user, tenant, profile, client


def upload(client, tenant, profile, fixture_name, report_type):
    content = (FIXTURES / fixture_name).read_bytes()
    file = SimpleUploadedFile(fixture_name, content, content_type="text/csv")
    return client.post(
        "/api/v1/reports/uploads",
        {
            "tenantId": str(tenant.pk),
            "profileId": str(profile.pk),
            "reportType": report_type,
            "file": file,
        },
        format="multipart",
        HTTP_IDEMPOTENCY_KEY=f"test-{fixture_name}-{ReportUpload.objects.count()}",
    )


@pytest.mark.django_db(transaction=True)
def test_campaign_upload_returns_202_and_imports_fixture(report_context):
    _, tenant, profile, client = report_context
    response = upload(
        client, tenant, profile, "campaign-valid.csv", ReportType.CAMPAIGN
    )

    assert response.status_code == 202
    task = ImportTask.objects.get(pk=response.json()["data"]["taskId"])
    assert task.status == ImportStatus.SUCCEEDED
    assert task.batch.succeeded_rows == 2
    assert Campaign.objects.filter(profile=profile).count() == 2
    assert isinstance(response.json()["data"]["taskId"], str)


@pytest.mark.django_db(transaction=True)
def test_partial_rows_are_recorded_without_rejecting_valid_rows(report_context):
    _, tenant, profile, client = report_context
    response = upload(
        client,
        tenant,
        profile,
        "campaign-partial-errors.csv",
        ReportType.CAMPAIGN,
    )

    task = ImportTask.objects.get(pk=response.json()["data"]["taskId"])
    assert task.status == ImportStatus.PARTIAL_SUCCEEDED
    assert (task.batch.succeeded_rows, task.batch.failed_rows) == (1, 1)
    assert task.batch.row_errors.get().field == "budget"


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("fixture_name", "report_type", "model", "expected"),
    [
        ("targeting-valid.csv", ReportType.TARGETING, Keyword, 1),
        ("targeting-valid.csv", ReportType.TARGETING, ProductTarget, 1),
        ("search-term-valid.csv", ReportType.SEARCH_TERM, SearchTerm, 2),
    ],
)
def test_targeting_and_search_term_fixtures(
    report_context, fixture_name, report_type, model, expected
):
    _, tenant, profile, client = report_context
    response = upload(client, tenant, profile, fixture_name, report_type)

    assert response.status_code == 202
    assert model.objects.count() == expected


@pytest.mark.django_db(transaction=True)
def test_duplicate_is_flagged_but_allowed_and_reprocess_is_append_only(
    report_context,
):
    _, tenant, profile, client = report_context
    first = upload(
        client, tenant, profile, "campaign-valid.csv", ReportType.CAMPAIGN
    )
    second = upload(
        client, tenant, profile, "duplicate-report.csv", ReportType.CAMPAIGN
    )
    second_task_id = second.json()["data"]["taskId"]
    reprocessed = client.post(
        f"/api/v1/reports/tasks/{second_task_id}/reprocess",
        HTTP_X_TENANT_ID=str(tenant.pk),
    )

    assert first.json()["data"]["isDuplicate"] is False
    assert second.json()["data"]["isDuplicate"] is True
    assert reprocessed.status_code == 202
    assert ImportTask.objects.count() == 3
    assert len({task.batch.pk for task in ImportTask.objects.all()}) == 3


@pytest.mark.django_db(transaction=True)
def test_profile_mismatch_is_failed_with_row_error(report_context):
    _, tenant, profile, client = report_context
    response = upload(
        client,
        tenant,
        profile,
        "unauthorized-profile-report.csv",
        ReportType.CAMPAIGN,
    )

    task = ImportTask.objects.get(pk=response.json()["data"]["taskId"])
    assert task.status == ImportStatus.FAILED
    assert task.batch.row_errors.get().code == "PROFILE_MISMATCH"


@pytest.mark.django_db
def test_cross_tenant_upload_returns_404(report_context):
    user, _, profile, client = report_context
    other = Tenant.objects.create(name="Other", tenant_type=TenantType.TEAM)
    TenantMembership.objects.create(
        tenant=other, user=user, role=MembershipRole.OWNER
    )
    response = upload(
        client, other, profile, "campaign-valid.csv", ReportType.CAMPAIGN
    )
    assert response.status_code == 404


def test_report_source_capabilities_are_explicit():
    assert FileUploadReportSource.capability.available is True
    assert ThirdPartyProviderReportSource.capability.mode == "reserved"
    assert AmazonAdsApiReportSource.capability.available is False


@pytest.mark.django_db(transaction=True)
def test_xlsx_campaign_import(report_context):
    _, tenant, profile, client = report_context
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        ["profile_id", "campaign_id", "campaign_name", "state", "budget", "currency"]
    )
    sheet.append(["DEMO-PROFILE-001", "XLSX-1", "Excel Campaign", "ENABLED", 12.5, "USD"])
    content = BytesIO()
    workbook.save(content)

    response = client.post(
        "/api/v1/reports/uploads",
        {
            "tenantId": str(tenant.pk),
            "profileId": str(profile.pk),
            "reportType": ReportType.CAMPAIGN,
            "file": SimpleUploadedFile(
                "campaign.xlsx",
                content.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        },
        format="multipart",
    )

    assert response.status_code == 202
    assert Campaign.objects.filter(external_campaign_id="XLSX-1").exists()
