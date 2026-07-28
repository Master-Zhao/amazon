from datetime import date
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory

from apps.actions import tasks as action_tasks
from apps.analytics import tasks as analytics_tasks
from apps.core.cache_keys import tenant_cache_key
from apps.core.pagination import page_spec, paginate_sequence
from apps.core.throttling import TenantUserRateThrottle
from apps.knowledge.models import KnowledgeArticle, KnowledgeCategory
from integrations.advertising_data.execution import (
    ExecutionAdapterRequest,
    ExecutionAdapterUnavailable,
    ManualExecutionAdapter,
    ReservedAmazonAdsExecutionAdapter,
)
from integrations.advertising_data.sources import (
    AmazonAdsApiReportSource,
    FileUploadReportSource,
    ReportFetchRequest,
    ReportSourceUnavailable,
    ThirdPartyProviderReportSource,
)
from integrations.llm.providers import (
    ExternalLLMProvider,
    LLMProviderUnavailable,
    MockLLMProvider,
)
from integrations.monitoring import LoggingMonitoringSink, MonitoringEvent
from integrations.storage.base import FileStorageUnavailable
from integrations.storage.object_storage import ObjectStorageFileStorage


def test_report_source_contract_is_scoped_idempotent_and_reserved_sources_are_offline():
    request = ReportFetchRequest(
        tenant_id="tenant-1",
        profile_id="profile-1",
        report_type="CAMPAIGN",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 2),
        idempotency_key="request-1",
        existing_storage_path="reports/file.csv",
    )
    result = FileUploadReportSource().fetch(request)

    assert result.storage_path == "reports/file.csv"
    assert result.external_request_id == "request-1"
    for source in (ThirdPartyProviderReportSource(), AmazonAdsApiReportSource()):
        with pytest.raises(ReportSourceUnavailable):
            source.fetch(request)
        assert source.max_retries == 2


def test_llm_and_execution_adapters_have_safe_mock_and_reserved_boundaries():
    mock_result = MockLLMProvider().generate(
        agent_code="STRATEGY",
        payload={
            "runId": "run-1",
            "campaigns": [
                {
                    "campaignId": "campaign-1",
                    "budgetSnapshot": "10.00",
                    "acos": "0.3",
                }
            ],
        },
    )
    assert mock_result["recommendations"][0]["afterValue"]["budget"] == "11.00"
    with pytest.raises(LLMProviderUnavailable):
        ExternalLLMProvider().generate(agent_code="STRATEGY", payload={})

    request = ExecutionAdapterRequest(
        tenant_id="tenant-1",
        profile_id="profile-1",
        action_type="PAUSE_CAMPAIGN",
        object_id="campaign-1",
        before_value={"state": "ENABLED"},
        after_value={"state": "PAUSED"},
        idempotency_key="execution-1",
    )
    manual = ManualExecutionAdapter().execute(request)
    assert manual.status == "REQUIRES_MANUAL"
    assert manual.evidence["tenantId"] == "tenant-1"
    with pytest.raises(ExecutionAdapterUnavailable):
        ReservedAmazonAdsExecutionAdapter().execute(request)


def test_object_storage_boundary_never_makes_a_real_call():
    storage = ObjectStorageFileStorage()
    with pytest.raises(FileStorageUnavailable):
        storage.save_stream(namespace="reports", filename="x.csv", chunks=[b"x"])
    assert storage.capability["mode"] == "reserved"


def test_tenant_cache_keys_and_rate_limits_are_isolated():
    first_key = tenant_cache_key(
        tenant_id="tenant-a", profile_id="profile-a", namespace="dashboard"
    )
    second_key = tenant_cache_key(
        tenant_id="tenant-b", profile_id="profile-a", namespace="dashboard"
    )
    assert first_key != second_key

    class OneRequestPerMinuteThrottle(TenantUserRateThrottle):
        def get_rate(self):
            return "1/min"

    cache.clear()
    factory = APIRequestFactory()
    user = SimpleNamespace(is_authenticated=True, pk=1)
    first = factory.get("/", HTTP_X_TENANT_ID="tenant-a")
    first.user = user
    repeated = factory.get("/", HTTP_X_TENANT_ID="tenant-a")
    repeated.user = user
    other_tenant = factory.get("/", HTTP_X_TENANT_ID="tenant-b")
    other_tenant.user = user

    assert OneRequestPerMinuteThrottle().allow_request(first, None)
    assert not OneRequestPerMinuteThrottle().allow_request(repeated, None)
    assert OneRequestPerMinuteThrottle().allow_request(other_tenant, None)


def test_pagination_contract_and_validation():
    request = Request(APIRequestFactory().get("/?page=2&pageSize=2"))
    spec = page_spec(request)
    items, pagination = paginate_sequence([1, 2, 3, 4, 5], spec)

    assert items == [3, 4]
    assert pagination == {
        "page": 2,
        "page_size": 2,
        "total": 5,
        "total_pages": 3,
    }

    invalid = Request(APIRequestFactory().get("/?page=0&pageSize=1000"))
    with pytest.raises(Exception) as error:
        page_spec(invalid)
    assert getattr(error.value, "status_code", None) == 400


def test_monitoring_sink_emits_structured_event(caplog):
    with caplog.at_level("INFO", logger="framework-test-monitoring"):
        LoggingMonitoringSink("framework-test-monitoring").emit(
            MonitoringEvent(
                name="queue.depth",
                value=3,
                tags={"queue": "analysis", "tenant": "redacted"},
            )
        )
    record = caplog.records[-1]
    assert record.metric_name == "queue.depth"
    assert record.metric_tags["queue"] == "analysis"


def test_celery_tasks_only_delegate_to_services(monkeypatch):
    evaluation_id = "00000000-0000-0000-0000-000000000001"
    monkeypatch.setattr(
        action_tasks,
        "evaluate_execution",
        lambda task_id: SimpleNamespace(pk=evaluation_id),
    )
    monkeypatch.setattr(
        analytics_tasks,
        "recalculate_profile_anomalies",
        lambda profile_id: 7,
    )

    assert action_tasks.evaluate_effects.run("task-1") == {
        "evaluationId": evaluation_id
    }
    assert analytics_tasks.recalculate_anomalies.run("profile-1") == {
        "processed": 7
    }


@pytest.mark.django_db
def test_knowledge_center_requires_authentication_and_returns_only_published_articles():
    category = KnowledgeCategory.objects.create(code="acos", name="ACOS", order=1)
    published = KnowledgeArticle.objects.create(
        category=category,
        slug="acos-basics",
        title="ACOS Basics",
        body="Published",
    )
    KnowledgeArticle.objects.create(
        category=category,
        slug="internal-draft",
        title="Draft",
        body="Hidden",
        published=False,
    )
    client = APIClient()

    assert client.get("/api/v1/knowledge/").status_code == 401
    user = get_user_model().objects.create_user(
        username="knowledge-reader",
        email="knowledge-reader@example.invalid",
        password="password",
    )
    client.force_authenticate(user)
    response = client.get("/api/v1/knowledge/")

    assert response.status_code == 200
    articles = [
        article
        for item in response.json()["data"]["categories"]
        for article in item["articles"]
    ]
    assert {
        "id": str(published.pk),
        "slug": "acos-basics",
        "title": "ACOS Basics",
        "body": "Published",
    } in articles
    assert all(article["slug"] != "internal-draft" for article in articles)
