import csv
import io
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from openpyxl import Workbook
from rest_framework.exceptions import NotFound
from rest_framework.serializers import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.actions.models import (
    ActionPreviewVersion,
    ActionPreviewStatus,
    ApprovalRecord,
    ApprovalDecision,
    ExecutionRecord,
    ExecutionOutcome,
)
from apps.actions.services import (
    create_action_preview,
    decide_action_preview,
    record_manual_execution,
    submit_action_preview,
)
from apps.advertising.models import (
    Campaign,
    Keyword,
    ProductTarget,
    SearchTerm,
)
from apps.agents.models import AgentRunStatus
from apps.agents.services import create_agent_run, process_agent_run
from apps.analytics.models import (
    AnomalyRecord,
    AnomalyRuleCode,
    AnomalyRuleVersion,
    AnomalyStatus,
    CampaignDailyMetric,
    CampaignMetricRevision,
    SearchTermDailyMetric,
    SearchTermMetricRevision,
    TargetingDailyMetric,
    TargetingMetricRevision,
)
from apps.analytics.services import (
    ensure_system_rules,
    metric_formulas,
    resolve_rule,
    resolve_target_acos,
)
from apps.analytics.selectors import campaign_metric_rows
from apps.audit.models import AuditLog
from apps.permissions.models import Permission, ProfileAccessLevel
from apps.products.models import (
    MarketplaceCatalogItem,
    Product,
    ProductListing,
)
from apps.reports.models import (
    ImportBatch,
    ImportRowError,
    ImportTaskStatus,
    ReportUpload,
)
from apps.reports.services import (
    create_report_import,
    process_report_import,
    reprocess_import,
)
from apps.recommendations.models import (
    LLMInvocation,
    Recommendation,
    RecommendationRevision,
)
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

pytestmark = pytest.mark.django_db
FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "reports"


def build_owner_scope(*, email="report-owner@example.invalid"):
    user = User.objects.create_user(
        username=email.split("@")[0],
        email=email,
        password="test-only-password",
    )
    tenant = Tenant.objects.create(name="Report tenant", tenant_type=TenantType.TEAM)
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        membership_role=MembershipRole.OWNER,
    )
    marketplace = Marketplace.objects.create(
        code=f"R{tenant.pk}",
        name="Report Marketplace",
        currency_code="USD",
        timezone="UTC",
    )
    store = AmazonStore.objects.create(
        tenant=tenant,
        name="Report Store",
        external_store_id=f"report-store-{tenant.pk}",
    )
    store_marketplace = StoreMarketplace.objects.create(
        store=store,
        marketplace=marketplace,
    )
    profile = AdvertisingProfile.objects.create(
        store_marketplace=store_marketplace,
        external_profile_id="DEMO-PROFILE-US-001",
        name="Report Profile",
        currency_code="USD",
        timezone="UTC",
        target_acos="0.2800",
    )
    Permission.objects.get_or_create(code="reports.upload", defaults={"name": "Upload"})
    Permission.objects.get_or_create(code="reports.view", defaults={"name": "View"})
    return user, tenant, profile


def uploaded_fixture(name: str) -> SimpleUploadedFile:
    content = (FIXTURES / name).read_bytes()
    return SimpleUploadedFile(name, content, content_type="text/csv")


def uploaded_xlsx_from_csv(name: str) -> SimpleUploadedFile:
    workbook = Workbook()
    worksheet = workbook.active
    with (FIXTURES / name).open(encoding="utf-8-sig", newline="") as source:
        for row in csv.reader(source):
            worksheet.append(row)
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    return SimpleUploadedFile(
        name.replace(".csv", ".xlsx"),
        output.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )


def request_for(user):
    return SimpleNamespace(user=user, request_id="test-report-request")


def use_test_storage(settings):
    settings.REPORT_STORAGE_ROOT = (
        settings.BASE_DIR / "test-artifacts" / "report-storage"
    )


def create_task(
    user,
    tenant,
    profile,
    filename,
    report_type="CAMPAIGN",
):
    return create_report_import(
        request=request_for(user),
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        report_type=report_type,
        uploaded_file=uploaded_fixture(filename),
    )


def test_valid_campaign_report_imports_master_data_and_audit(settings):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    task = create_task(user, tenant, profile, "campaign-valid.csv")

    result = process_report_import(task_id=task.pk)

    assert result.status == ImportTaskStatus.SUCCEEDED
    assert (result.total_rows, result.success_rows, result.error_rows) == (2, 2, 0)
    assert set(
        Campaign.objects.filter(profile=profile).values_list(
            "external_campaign_id", flat=True
        )
    ) == {"campaign-001", "campaign-002"}
    assert result.batch.schema_version == "campaign-v1"
    assert CampaignDailyMetric.objects.filter(profile=profile).count() == 2
    assert CampaignMetricRevision.objects.filter(
        source_batch=result.batch
    ).count() == 2
    assert AnomalyRecord.objects.filter(
        metric__profile=profile,
        rule_version__code=AnomalyRuleCode.HIGH_ACOS,
        status=AnomalyStatus.ANOMALY,
    ).count() == 2
    assert AnomalyRecord.objects.filter(
        metric__profile=profile,
        rule_version__code=AnomalyRuleCode.BUDGET_EARLY_EXHAUSTION,
        status=AnomalyStatus.ANOMALY,
        reason_code="BUDGET_EXHAUSTED_EARLY",
    ).count() == 1
    assert CampaignDailyMetric.objects.get(
        campaign__external_campaign_id="campaign-001"
    ).snapshot_hour_local == 12
    assert AuditLog.objects.filter(
        event="report.uploaded", object_id=str(task.upload_id)
    ).exists()
    assert AuditLog.objects.filter(
        event="report.import_completed", object_id=str(task.pk)
    ).exists()


def test_partial_campaign_report_keeps_valid_rows_and_records_error(
    settings,
):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    task = create_task(user, tenant, profile, "campaign-partial-errors.csv")

    result = process_report_import(task_id=task.pk)

    assert result.status == ImportTaskStatus.PARTIAL_SUCCEEDED
    assert (result.total_rows, result.success_rows, result.error_rows) == (2, 1, 1)
    error = ImportRowError.objects.get(task=result)
    assert error.row_number == 3
    assert error.error_code == "ROW_VALIDATION_ERROR"
    assert Campaign.objects.filter(
        profile=profile,
        external_campaign_id="campaign-003",
    ).exists()


def test_profile_id_mismatch_fails_without_publishing_campaign(settings):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    task = create_task(user, tenant, profile, "unauthorized-profile-report.csv")

    result = process_report_import(task_id=task.pk)

    assert result.status == ImportTaskStatus.FAILED
    assert result.error_code == "ALL_ROWS_INVALID"
    assert result.error_rows == 1
    assert not Campaign.objects.filter(profile=profile).exists()


def test_missing_required_headers_fail_the_whole_file(settings):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    malformed = SimpleUploadedFile(
        "missing-columns.csv",
        b"date,campaign_id\n2026-07-20,campaign-001\n",
        content_type="text/csv",
    )
    task = create_report_import(
        request=request_for(user),
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        report_type="CAMPAIGN",
        uploaded_file=malformed,
    )

    result = process_report_import(task_id=task.pk)

    assert result.status == ImportTaskStatus.FAILED
    assert result.error_code == "REPORT_STRUCTURE_ERROR"
    assert not hasattr(result, "batch")


@pytest.mark.parametrize(
    "uploaded_file",
    [
        SimpleUploadedFile(
            "report.csv",
            b"not,really,binary\x00content",
            content_type="text/csv",
        ),
        SimpleUploadedFile(
            "report.xlsx",
            b"not-a-zip-workbook",
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        ),
        SimpleUploadedFile(
            "report.csv",
            b"date,campaign_id\n",
            content_type="image/png",
        ),
    ],
)
def test_upload_rejects_mime_or_magic_mismatch_before_storage(
    settings,
    uploaded_file,
):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()

    with pytest.raises(ValidationError):
        create_report_import(
            request=request_for(user),
            tenant_id=tenant.pk,
            profile_id=profile.pk,
            report_type="CAMPAIGN",
            uploaded_file=uploaded_file,
        )

    assert not ReportUpload.objects.filter(profile=profile).exists()


def test_upload_sanitizes_client_filename_and_storage_key(settings):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    uploaded = SimpleUploadedFile(
        "../../escape.csv",
        (FIXTURES / "campaign-valid.csv").read_bytes(),
        content_type="text/csv",
    )

    task = create_report_import(
        request=request_for(user),
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        report_type="CAMPAIGN",
        uploaded_file=uploaded,
    )

    assert task.upload.original_filename == "escape.csv"
    assert ".." not in task.upload.storage_key
    assert "escape.csv" not in task.upload.storage_key


def test_upload_outside_tenant_scope_returns_not_found(settings):
    use_test_storage(settings)
    _, tenant, profile = build_owner_scope()
    outsider = User.objects.create_user(
        username="report-outsider",
        email="report-outsider@example.invalid",
        password="test-only-password",
    )

    with pytest.raises(NotFound):
        create_report_import(
            request=request_for(outsider),
            tenant_id=tenant.pk,
            profile_id=profile.pk,
            report_type="CAMPAIGN",
            uploaded_file=uploaded_fixture("campaign-valid.csv"),
        )

    assert not ReportUpload.objects.filter(uploaded_by=outsider).exists()


def test_invalid_utf8_fails_as_read_error_without_batch(settings):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    uploaded = SimpleUploadedFile(
        "invalid-utf8.csv",
        (FIXTURES / "campaign-valid.csv").read_bytes() + b"\xff",
        content_type="text/csv",
    )
    task = create_report_import(
        request=request_for(user),
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        report_type="CAMPAIGN",
        uploaded_file=uploaded,
    )

    result = process_report_import(task_id=task.pk)

    assert result.status == ImportTaskStatus.FAILED
    assert result.error_code == "REPORT_READ_ERROR"
    assert not ImportBatch.objects.filter(task=result).exists()


@pytest.mark.parametrize(
    ("report_type", "fixture_name", "expected_rows"),
    [
        ("CAMPAIGN", "campaign-valid.csv", 2),
        ("TARGETING", "targeting-valid.csv", 2),
        ("SEARCH_TERM", "search-term-valid.csv", 1),
    ],
)
def test_all_three_report_types_accept_xlsx(
    settings,
    report_type,
    fixture_name,
    expected_rows,
):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope(
        email=f"{report_type.lower()}-xlsx@example.invalid"
    )
    task = create_report_import(
        request=request_for(user),
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        report_type=report_type,
        uploaded_file=uploaded_xlsx_from_csv(fixture_name),
    )

    result = process_report_import(task_id=task.pk)

    assert result.status == ImportTaskStatus.SUCCEEDED
    assert result.success_rows == expected_rows


def test_duplicate_upload_is_traced_and_does_not_duplicate_campaigns(
    settings,
):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    first = create_task(user, tenant, profile, "campaign-valid.csv")
    process_report_import(task_id=first.pk)
    duplicate = create_task(user, tenant, profile, "duplicate-report.csv")

    result = process_report_import(task_id=duplicate.pk)

    assert result.status == ImportTaskStatus.SUCCEEDED
    assert ReportUpload.objects.get(pk=duplicate.upload_id).duplicate_of_id == first.upload_id
    assert Campaign.objects.filter(profile=profile).count() == 2


def test_processing_same_task_twice_is_idempotent(settings):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    task = create_task(user, tenant, profile, "campaign-valid.csv")

    first = process_report_import(task_id=task.pk)
    second = process_report_import(task_id=task.pk)

    assert first.status == second.status == ImportTaskStatus.SUCCEEDED
    assert ImportBatch.objects.filter(task=task).count() == 1
    assert CampaignMetricRevision.objects.filter(
        source_batch=first.batch
    ).count() == 2


def test_reprocess_creates_new_task_batch_and_metric_revisions(settings):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    original = create_task(user, tenant, profile, "campaign-valid.csv")
    original = process_report_import(task_id=original.pk)

    repeated = reprocess_import(
        request=request_for(user),
        tenant_id=tenant.pk,
        task_id=original.pk,
    )
    repeated = process_report_import(task_id=repeated.pk)

    assert repeated.pk != original.pk
    assert repeated.upload_id == original.upload_id
    assert repeated.reprocessed_from_id == original.pk
    assert repeated.batch.pk != original.batch.pk
    assert CampaignDailyMetric.objects.filter(profile=profile).count() == 2
    assert CampaignMetricRevision.objects.filter(
        metric__profile=profile
    ).count() == 4


def test_upload_api_returns_202_and_enforces_cross_tenant_404(settings):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    _, other_tenant, other_profile = build_owner_scope(
        email="other-report-owner@example.invalid"
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        f"/api/v1/reports/tenants/{tenant.pk}/profiles/{profile.pk}/uploads",
        {"reportType": "CAMPAIGN", "file": uploaded_fixture("campaign-valid.csv")},
        format="multipart",
    )
    hidden = client.post(
        f"/api/v1/reports/tenants/{tenant.pk}/profiles/{other_profile.pk}/uploads",
        {"reportType": "CAMPAIGN", "file": uploaded_fixture("campaign-valid.csv")},
        format="multipart",
    )

    assert response.status_code == 202
    assert response.data["data"]["status"] == ImportTaskStatus.QUEUED
    assert hidden.status_code == 404
    assert other_tenant.pk != tenant.pk


def test_task_list_and_error_api_are_profile_scoped(settings):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    task = create_task(user, tenant, profile, "campaign-partial-errors.csv")
    process_report_import(task_id=task.pk)
    client = APIClient()
    client.force_authenticate(user=user)

    tasks = client.get(
        f"/api/v1/reports/tenants/{tenant.pk}/profiles/{profile.pk}/tasks"
    )
    errors = client.get(
        f"/api/v1/reports/tenants/{tenant.pk}/tasks/{task.pk}/errors"
    )
    source = client.get(
        f"/api/v1/reports/tenants/{tenant.pk}/tasks/{task.pk}/source"
    )

    assert tasks.status_code == 200
    assert tasks.data["data"][0]["status"] == ImportTaskStatus.PARTIAL_SUCCEEDED
    assert errors.status_code == 200
    assert errors.data["data"][0]["row_number"] == 3
    assert source.status_code == 200
    assert b"".join(source.streaming_content) == (
        FIXTURES / "campaign-partial-errors.csv"
    ).read_bytes()


def test_metric_formulas_return_null_and_reason_for_zero_denominators():
    formulas = metric_formulas(
        impressions=0,
        clicks=0,
        spend=0,
        orders=0,
        sales=0,
    )

    assert formulas["ctr"] == {"value": None, "reason": "NO_IMPRESSIONS"}
    assert formulas["cpc"] == {"value": None, "reason": "NO_CLICKS"}
    assert formulas["cvr"] == {"value": None, "reason": "NO_CLICKS"}
    assert formulas["acos"] == {"value": None, "reason": "NO_SALES"}
    assert formulas["roas"] == {"value": None, "reason": "NO_SPEND"}


def test_zero_denominator_reasons_are_persisted_and_exposed(settings):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    content = (
        "date,profile_id,campaign_id,campaign_name,campaign_status,"
        "daily_budget,snapshot_hour_local,currency,impressions,clicks,"
        "spend,orders,sales\n"
        "2026-07-21,DEMO-PROFILE-US-001,zero-campaign,Zero Campaign,"
        "ENABLED,10.00,12,USD,0,0,0,0,0\n"
    ).encode()
    task = create_report_import(
        request=request_for(user),
        tenant_id=tenant.pk,
        profile_id=profile.pk,
        report_type="CAMPAIGN",
        uploaded_file=SimpleUploadedFile(
            "zero-denominators.csv",
            content,
            content_type="text/csv",
        ),
    )

    result = process_report_import(task_id=task.pk)
    metric = CampaignDailyMetric.objects.get(profile=profile)
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(
        f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{profile.pk}/campaigns"
    )

    assert result.status == ImportTaskStatus.SUCCEEDED
    assert metric.calculation_reasons == {
        "ctr": "NO_IMPRESSIONS",
        "cpc": "NO_CLICKS",
        "cvr": "NO_CLICKS",
        "acos": "NO_SALES",
        "roas": "NO_SPEND",
    }
    assert response.data["data"][0]["calculation_reasons"] == (
        metric.calculation_reasons
    )


def test_campaign_metric_api_returns_formula_lineage_and_anomaly(settings):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    task = create_task(user, tenant, profile, "campaign-valid.csv")
    result = process_report_import(task_id=task.pk)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(
        f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{profile.pk}/campaigns"
    )

    assert response.status_code == 200
    assert len(response.data["data"]) == 2
    row = response.data["data"][0]
    assert row["acos"]["value"] is not None
    assert row["target_acos"] == "0.2800"
    assert row["source_batch_id"] == str(result.batch.pk)
    assert any(
        item["rule_code"] == AnomalyRuleCode.HIGH_ACOS
        and item["status"] == AnomalyStatus.ANOMALY
        for item in row["anomalies"]
    )

    process_report_import(
        task_id=create_task(
            user,
            tenant,
            profile,
            "targeting-valid.csv",
            report_type="TARGETING",
        ).pk
    )
    process_report_import(
        task_id=create_task(
            user,
            tenant,
            profile,
            "search-term-valid.csv",
            report_type="SEARCH_TERM",
        ).pk
    )
    dashboard = client.get(
        f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{profile.pk}/dashboard"
    )
    assert dashboard.status_code == 200
    summary = dashboard.data["data"][0]
    assert summary["spend"] == "117.5"
    assert summary["sales"] == "346"
    assert summary["campaign_count"] == 2
    assert summary["authoritative_grain"] == "CAMPAIGN_DAILY_METRIC"


def test_target_acos_and_rule_scope_use_most_specific_configuration(settings):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    task = create_task(user, tenant, profile, "campaign-valid.csv")
    process_report_import(task_id=task.pk)
    campaign = Campaign.objects.select_related(
        "profile__store_marketplace__store__tenant"
    ).get(profile=profile, external_campaign_id="campaign-001")

    assert resolve_target_acos(campaign) == Decimal("0.2800")
    campaign.target_acos = Decimal("0.2500")
    campaign.save(update_fields=["target_acos"])
    assert resolve_target_acos(campaign) == Decimal("0.2500")
    campaign.target_acos = None
    campaign.save(update_fields=["target_acos"])
    profile.target_acos = None
    profile.save(update_fields=["target_acos"])
    tenant.target_acos = Decimal("0.3300")
    tenant.save(update_fields=["target_acos"])
    campaign.refresh_from_db()
    assert resolve_target_acos(campaign) == Decimal("0.3300")

    system_rule = ensure_system_rules()[AnomalyRuleCode.HIGH_ACOS]
    AnomalyRuleVersion.objects.create(
        code=AnomalyRuleCode.HIGH_ACOS,
        version=2,
        scope_key=f"TENANT:{tenant.pk}",
        tenant=tenant,
        configuration={"minimum_clicks": 8, "minimum_sales": "0.01"},
    )
    AnomalyRuleVersion.objects.create(
        code=AnomalyRuleCode.HIGH_ACOS,
        version=2,
        scope_key=f"PROFILE:{profile.pk}",
        profile=profile,
        configuration={"minimum_clicks": 6, "minimum_sales": "0.01"},
    )
    campaign_rule = AnomalyRuleVersion.objects.create(
        code=AnomalyRuleCode.HIGH_ACOS,
        version=2,
        scope_key=f"CAMPAIGN:{campaign.pk}",
        campaign=campaign,
        configuration={"minimum_clicks": 4, "minimum_sales": "0.01"},
    )

    assert resolve_rule(
        code=AnomalyRuleCode.HIGH_ACOS,
        campaign=campaign,
        system_rule=system_rule,
    ) == campaign_rule


def test_dashboard_never_combines_marketplaces_or_currencies(settings):
    use_test_storage(settings)
    user, tenant, usd_profile = build_owner_scope()
    eur_marketplace = Marketplace.objects.create(
        code="EU-DE",
        name="Germany",
        currency_code="EUR",
        timezone="Europe/Berlin",
    )
    eur_store = AmazonStore.objects.create(
        tenant=tenant,
        name="EU Store",
        external_store_id="demo-store-eu",
    )
    eur_store_marketplace = StoreMarketplace.objects.create(
        store=eur_store,
        marketplace=eur_marketplace,
    )
    eur_profile = AdvertisingProfile.objects.create(
        store_marketplace=eur_store_marketplace,
        external_profile_id="DEMO-PROFILE-EU-001",
        name="EU Profile",
        currency_code="EUR",
        timezone="Europe/Berlin",
    )
    process_report_import(
        task_id=create_task(
            user,
            tenant,
            usd_profile,
            "campaign-valid.csv",
        ).pk
    )
    eur_content = (
        (FIXTURES / "campaign-valid.csv")
        .read_text(encoding="utf-8")
        .replace("DEMO-PROFILE-US-001", "DEMO-PROFILE-EU-001")
        .replace(",USD,", ",EUR,")
        .encode()
    )
    eur_task = create_report_import(
        request=request_for(user),
        tenant_id=tenant.pk,
        profile_id=eur_profile.pk,
        report_type="CAMPAIGN",
        uploaded_file=SimpleUploadedFile(
            "campaign-eur.csv",
            eur_content,
            content_type="text/csv",
        ),
    )
    process_report_import(task_id=eur_task.pk)
    client = APIClient()
    client.force_authenticate(user=user)

    usd = client.get(
        f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{usd_profile.pk}/dashboard"
    )
    eur = client.get(
        f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{eur_profile.pk}/dashboard"
    )

    assert [row["currency_code"] for row in usd.data["data"]] == ["USD"]
    assert [row["marketplace_code"] for row in usd.data["data"]] == [
        usd_profile.store_marketplace.marketplace.code
    ]
    assert [row["currency_code"] for row in eur.data["data"]] == ["EUR"]
    assert [row["marketplace_code"] for row in eur.data["data"]] == ["EU-DE"]
    assert usd.data["data"][0]["spend"] == "117.5"
    assert eur.data["data"][0]["spend"] == "117.5"


def test_targeting_report_imports_keyword_product_target_and_daily_facts(settings):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    task = create_task(
        user,
        tenant,
        profile,
        "targeting-valid.csv",
        report_type="TARGETING",
    )

    result = process_report_import(task_id=task.pk)

    assert result.status == ImportTaskStatus.SUCCEEDED
    assert (result.total_rows, result.success_rows, result.error_rows) == (2, 2, 0)
    assert result.batch.schema_version == "targeting-v1"
    keyword = Keyword.objects.get(
        ad_group__campaign__profile=profile,
        external_keyword_id="keyword-001",
    )
    product_target = ProductTarget.objects.get(
        ad_group__campaign__profile=profile,
        external_target_id="target-001",
    )
    metrics = TargetingDailyMetric.objects.filter(profile=profile)
    assert metrics.count() == 2
    assert metrics.get(keyword=keyword).bid_snapshot == Decimal("1.2500")
    assert metrics.get(product_target=product_target).state_snapshot == "PAUSED"
    assert TargetingMetricRevision.objects.filter(
        source_batch=result.batch
    ).count() == 2
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(
        f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{profile.pk}/targeting"
    )
    assert response.status_code == 200
    assert len(response.data["data"]) == 2
    assert {row["target_type"] for row in response.data["data"]} == {
        "KEYWORD",
        "PRODUCT_TARGET",
    }
    assert all(
        row["source_batch_id"] == str(result.batch.pk)
        for row in response.data["data"]
    )
    master = client.get(
        f"/api/v1/advertising/tenants/{tenant.pk}/profiles/{profile.pk}/targeting"
    )
    campaigns = client.get(
        f"/api/v1/advertising/tenants/{tenant.pk}/profiles/{profile.pk}/campaigns"
    )
    assert master.status_code == 200
    assert {row["target_type"] for row in master.data["data"]} == {
        "KEYWORD",
        "PRODUCT_TARGET",
    }
    assert campaigns.status_code == 200
    assert campaigns.data["data"][0]["source_batch_id"] == str(result.batch.pk)


def test_search_term_report_imports_distinct_master_and_authoritative_fact(settings):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    task = create_task(
        user,
        tenant,
        profile,
        "search-term-valid.csv",
        report_type="SEARCH_TERM",
    )

    result = process_report_import(task_id=task.pk)

    assert result.status == ImportTaskStatus.SUCCEEDED
    assert result.batch.schema_version == "search-term-v1"
    search_term = SearchTerm.objects.get(profile=profile)
    assert search_term.display_text == "best running shoes"
    assert search_term.normalized_text == "best running shoes"
    metric = SearchTermDailyMetric.objects.get(
        profile=profile,
        search_term=search_term,
    )
    assert metric.targeting_expression_snapshot == "running shoes"
    assert metric.spend == Decimal("12.0000")
    assert SearchTermMetricRevision.objects.filter(
        source_batch=result.batch
    ).count() == 1
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(
        f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{profile.pk}/search-terms"
    )
    assert response.status_code == 200
    row = response.data["data"][0]
    assert row["search_term"] == "best running shoes"
    assert row["source_batch_id"] == str(result.batch.pk)
    assert row["acos"]["value"] == "0.16"
    master = client.get(
        f"/api/v1/advertising/tenants/{tenant.pk}/profiles/{profile.pk}/search-terms"
    )
    assert master.status_code == 200
    assert master.data["data"][0]["display_text"] == "best running shoes"


def test_campaign_detail_and_analytics_configuration_are_scoped_and_audited(
    settings,
):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    result = process_report_import(
        task_id=create_task(
            user,
            tenant,
            profile,
            "campaign-valid.csv",
        ).pk
    )
    campaign = Campaign.objects.get(
        profile=profile,
        external_campaign_id="campaign-001",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    detail = client.get(
        f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{profile.pk}/"
        f"campaigns/{campaign.pk}"
    )
    configuration = client.get(
        f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{profile.pk}/"
        "configuration"
    )

    assert detail.status_code == 200
    assert detail.data["data"]["campaign_id"] == str(campaign.pk)
    assert len(detail.data["data"]["metrics"]) == 1
    assert detail.data["data"]["metrics"][0]["source_batch_id"] == str(
        result.batch.pk
    )
    assert configuration.status_code == 200
    assert configuration.data["data"]["profile_target_acos"] == "0.2800"

    target_update = client.put(
        f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{profile.pk}/"
        "configuration/target-acos",
        {
            "scopeType": "CAMPAIGN",
            "campaignId": str(campaign.pk),
            "targetAcos": "0.2400",
        },
        format="json",
    )
    assert target_update.status_code == 200
    campaign.refresh_from_db()
    assert campaign.target_acos == Decimal("0.2400")
    updated_campaign = next(
        item
        for item in target_update.data["data"]["campaigns"]
        if item["campaign_id"] == str(campaign.pk)
    )
    assert updated_campaign["effective_target_acos"] == "0.2400"

    first_rule = client.post(
        f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{profile.pk}/"
        "configuration/rules",
        {
            "code": "HIGH_SPEND_NO_ORDERS",
            "scopeType": "PROFILE",
            "configuration": {"minimum_spend": "44.00"},
        },
        format="json",
    )
    second_rule = client.post(
        f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{profile.pk}/"
        "configuration/rules",
        {
            "code": "HIGH_SPEND_NO_ORDERS",
            "scopeType": "PROFILE",
            "configuration": {"minimum_spend": "55.00"},
        },
        format="json",
    )
    assert first_rule.status_code == second_rule.status_code == 201
    assert first_rule.data["data"]["version"] == 1
    assert second_rule.data["data"]["version"] == 2
    assert AnomalyRuleVersion.objects.get(
        pk=first_rule.data["data"]["id"]
    ).configuration["minimum_spend"] == "44.00"
    assert AuditLog.objects.filter(
        tenant=tenant,
        event="analytics.target_acos_configured",
    ).exists()
    assert AuditLog.objects.filter(
        tenant=tenant,
        event="analytics.rule_version_created",
    ).count() == 2


def test_analytics_configuration_rejects_cross_profile_and_invalid_rule(
    settings,
):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    process_report_import(
        task_id=create_task(
            user,
            tenant,
            profile,
            "campaign-valid.csv",
        ).pk
    )
    _, _, other_profile = build_owner_scope(
        email="other-analytics-owner@example.invalid"
    )
    other_campaign = Campaign.objects.create(
        profile=other_profile,
        external_campaign_id="other-campaign",
        name="Other Campaign",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    hidden = client.get(
        f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{profile.pk}/"
        f"campaigns/{other_campaign.pk}"
    )
    hidden_update = client.put(
        f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{profile.pk}/"
        "configuration/target-acos",
        {
            "scopeType": "CAMPAIGN",
            "campaignId": str(other_campaign.pk),
            "targetAcos": "0.2500",
        },
        format="json",
    )
    invalid_rule = client.post(
        f"/api/v1/analytics/tenants/{tenant.pk}/profiles/{profile.pk}/"
        "configuration/rules",
        {
            "code": "HIGH_ACOS",
            "scopeType": "PROFILE",
            "configuration": {"unknownThreshold": "1"},
        },
        format="json",
    )

    assert hidden.status_code == 404
    assert hidden_update.status_code == 404
    assert invalid_rule.status_code == 400


def test_campaign_selector_query_count_does_not_grow_with_rows(settings):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    result = process_report_import(
        task_id=create_task(
            user,
            tenant,
            profile,
            "campaign-valid.csv",
        ).pk
    )
    with CaptureQueriesContext(connection) as initial_queries:
        campaign_metric_rows(
            user=user,
            tenant_id=tenant.pk,
            profile_id=profile.pk,
        )
    for index in range(10):
        campaign = Campaign.objects.create(
            profile=profile,
            external_campaign_id=f"query-count-{index}",
            name=f"Query Count {index}",
        )
        CampaignDailyMetric.objects.create(
            profile=profile,
            campaign=campaign,
            report_date=timezone.localdate(),
            currency_code="USD",
            impressions=100,
            clicks=10,
            spend="10.0000",
            orders=1,
            sales="30.0000",
            state_snapshot="ENABLED",
            source_batch=result.batch,
        )
    with CaptureQueriesContext(connection) as expanded_queries:
        rows = campaign_metric_rows(
            user=user,
            tenant_id=tenant.pk,
            profile_id=profile.pk,
        )

    assert len(rows) == 12
    assert len(expanded_queries) == len(initial_queries)


def test_mock_recommendation_preview_approval_execution_and_audit(
    settings,
):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    tenant.tenant_type = TenantType.PERSONAL
    tenant.save(update_fields=["tenant_type"])
    task = create_task(user, tenant, profile, "campaign-valid.csv")
    process_report_import(task_id=task.pk)
    request = request_for(user)

    run = create_agent_run(
        request=request,
        tenant_id=tenant.pk,
        profile_id=profile.pk,
    )
    run = process_agent_run(run_id=run.pk)

    assert run.status == AgentRunStatus.SUCCEEDED
    assert LLMInvocation.objects.filter(agent_run=run).count() == 4
    recommendation = Recommendation.objects.filter(agent_run=run).first()
    assert recommendation is not None
    preview = create_action_preview(
        request=request,
        tenant_id=tenant.pk,
        recommendation_id=recommendation.pk,
    )
    preview = submit_action_preview(
        request=request,
        tenant_id=tenant.pk,
        preview_id=preview.pk,
    )
    assert preview.status == ActionPreviewStatus.PENDING_APPROVAL
    preview, approval = decide_action_preview(
        request=request,
        tenant_id=tenant.pk,
        preview_id=preview.pk,
        decision=ApprovalDecision.APPROVED,
        comment="Demo owner confirms the proposed budget.",
        idempotency_key="approval-demo-1",
    )
    assert approval.decision == ApprovalDecision.APPROVED
    assert preview.status == ActionPreviewStatus.APPROVED
    preview, execution = record_manual_execution(
        request=request,
        tenant_id=tenant.pk,
        preview_id=preview.pk,
        outcome=ExecutionOutcome.SUCCESS,
        actual_value={"dailyBudget": "45.00", "currency": "USD"},
        executed_at=timezone.now(),
        note="Applied manually in the fictional Amazon console.",
        evidence_metadata={"filename": "demo-confirmation.txt"},
        idempotency_key="execution-demo-1",
    )
    assert execution.outcome == ExecutionOutcome.SUCCESS
    assert AuditLog.objects.filter(
        event="agent_run.completed", object_id=str(run.pk)
    ).exists()
    assert AuditLog.objects.filter(
        event="action_preview.execution_recorded",
        object_id=str(preview.pk),
    ).exists()

    immutable_records = [
        task.upload,
        LLMInvocation.objects.filter(agent_run=run).first(),
        RecommendationRevision.objects.get(recommendation=recommendation),
        ActionPreviewVersion.objects.get(preview=preview),
        ApprovalRecord.objects.get(pk=approval.pk),
        ExecutionRecord.objects.get(pk=execution.pk),
    ]
    for record in immutable_records:
        with pytest.raises(TypeError, match="append-only"):
            record.save()
        with pytest.raises(TypeError, match="append-only"):
            record.delete()


def test_demo_workflow_apis_reach_services_and_append_audit(settings):
    use_test_storage(settings)
    user, tenant, profile = build_owner_scope()
    tenant.tenant_type = TenantType.PERSONAL
    tenant.save(update_fields=["tenant_type"])
    task = create_task(user, tenant, profile, "campaign-valid.csv")
    process_report_import(task_id=task.pk)
    client = APIClient()
    client.force_authenticate(user=user)

    queued = client.post(
        f"/api/v1/analysis/tenants/{tenant.pk}/profiles/{profile.pk}/runs"
    )
    assert queued.status_code == 202
    run = process_agent_run(run_id=int(queued.data["data"]["id"]))
    assert run.status == AgentRunStatus.SUCCEEDED

    recommendation_response = client.get(
        f"/api/v1/recommendations/tenants/{tenant.pk}/profiles/{profile.pk}"
    )
    recommendation_id = recommendation_response.data["data"][0]["id"]
    created = client.post(
        f"/api/v1/actions/tenants/{tenant.pk}/recommendations/"
        f"{recommendation_id}/previews"
    )
    assert created.status_code == 201
    preview_id = created.data["data"]["id"]

    submitted = client.post(
        f"/api/v1/actions/tenants/{tenant.pk}/previews/{preview_id}/submit"
    )
    assert submitted.data["data"]["status"] == ActionPreviewStatus.PENDING_APPROVAL
    approved = client.post(
        f"/api/v1/actions/tenants/{tenant.pk}/previews/{preview_id}/decision",
        {
            "decision": "APPROVED",
            "comment": "API demo approval",
            "idempotencyKey": "api-approval-demo",
        },
        format="json",
    )
    assert approved.status_code == 200
    assert approved.data["data"]["status"] == ActionPreviewStatus.APPROVED
    executed = client.post(
        f"/api/v1/actions/tenants/{tenant.pk}/previews/{preview_id}/executions",
        {
            "outcome": "SUCCESS",
            "actualValue": {"dailyBudget": "45.00", "currency": "USD"},
            "executedAt": timezone.now().isoformat(),
            "note": "API demo execution",
            "evidenceMetadata": {},
            "idempotencyKey": "api-execution-demo",
        },
        format="json",
    )
    assert executed.status_code == 201
    assert executed.data["data"]["executions"][0]["outcome"] == "SUCCESS"

    audit = client.get(f"/api/v1/audit/tenants/{tenant.pk}")
    assert audit.status_code == 200
    events = {item["event"] for item in audit.data["data"]}
    assert {
        "agent_run.completed",
        "action_preview.created",
        "action_preview.submitted",
        "action_preview.decided",
        "action_preview.execution_recorded",
    }.issubset(events)


def test_product_api_enforces_tenant_scope_and_listing_cardinalities():
    user, tenant, profile = build_owner_scope()
    client = APIClient()
    client.force_authenticate(user=user)
    store_marketplace_id = profile.store_marketplace_id

    created = client.post(
        f"/api/v1/products/tenants/{tenant.pk}",
        {
            "name": "Demo Shoe",
            "storeMarketplaceId": str(store_marketplace_id),
            "sellerSku": "DEMO-SKU-001",
            "asin": "demoasin001",
            "catalogTitle": "Demo Running Shoe",
        },
        format="json",
    )
    assert created.status_code == 201
    product_id = created.data["data"]["id"]
    second = client.post(
        f"/api/v1/products/tenants/{tenant.pk}/{product_id}/listings",
        {
            "storeMarketplaceId": str(store_marketplace_id),
            "sellerSku": "DEMO-SKU-002",
            "asin": "DEMOASIN001",
            "catalogTitle": "Ignored duplicate title",
        },
        format="json",
    )

    assert second.status_code == 201
    assert len(second.data["data"]["listings"]) == 2
    assert Product.objects.filter(tenant=tenant).count() == 1
    assert ProductListing.objects.filter(product_id=product_id).count() == 2
    assert MarketplaceCatalogItem.objects.filter(
        marketplace=profile.store_marketplace.marketplace,
        asin="DEMOASIN001",
    ).count() == 1

    duplicate_sku = client.post(
        f"/api/v1/products/tenants/{tenant.pk}/{product_id}/listings",
        {
            "storeMarketplaceId": str(store_marketplace_id),
            "sellerSku": "DEMO-SKU-001",
        },
        format="json",
    )
    assert duplicate_sku.status_code == 400

    _, other_tenant, _ = build_owner_scope(
        email="other-product-owner@example.invalid"
    )
    hidden = client.get(f"/api/v1/products/tenants/{other_tenant.pk}")
    assert hidden.status_code == 404
    assert AuditLog.objects.filter(
        tenant=tenant,
        event__in={"product.created", "product.listing_added"},
    ).count() == 2
