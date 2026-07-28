import io
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
    ThirdPartyReportSource,
)
from integrations.llm.providers import MockLLMProvider
from integrations.storage.base import FileStorageUnavailable
from integrations.storage.object_storage import ObjectStorageFileStorage


class MemoryStorage:
    def __init__(self):
        self.content = {"reports/file.csv": b"fixture"}

    def open(self, *, key):
        return io.BytesIO(self.content[key])


def test_report_source_boundary_reads_uploaded_content_and_reserved_sources_are_offline():
    source = FileUploadReportSource(
        storage=MemoryStorage(),
        storage_key="reports/file.csv",
    )
    assert source.open().read() == b"fixture"
    for reserved in (ThirdPartyReportSource(), AmazonAdsApiReportSource()):
        with pytest.raises(NotImplementedError):
            reserved.open()


def test_llm_and_execution_adapters_have_safe_mock_and_reserved_boundaries():
    mock_result = MockLLMProvider().generate(
        agent_code="DATA_ANALYSIS",
        run_id="run-1",
        context={},
    )
    assert mock_result["schemaVersion"] == "agent-result-v1"
    assert mock_result["agentCode"] == "DATA_ANALYSIS"

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
        storage.save_stream(
            namespace="reports",
            filename="x.csv",
            chunks=[b"x"],
        )
    assert storage.capability["mode"] == "reserved"


def test_tenant_cache_keys_and_rate_limits_are_isolated():
    first_key = tenant_cache_key(
        tenant_id="tenant-a",
        profile_id="profile-a",
        namespace="dashboard",
    )
    second_key = tenant_cache_key(
        tenant_id="tenant-b",
        profile_id="profile-a",
        namespace="dashboard",
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
    with pytest.raises(Exception) as error:
        page_spec(Request(APIRequestFactory().get("/?page=0&pageSize=1000")))
    assert getattr(error.value, "status_code", None) == 400


def test_celery_tasks_only_delegate_to_services(monkeypatch):
    monkeypatch.setattr(
        action_tasks,
        "evaluate_execution",
        lambda record_id: SimpleNamespace(pk="evaluation-1"),
    )
    monkeypatch.setattr(
        analytics_tasks,
        "recalculate_profile_anomalies",
        lambda profile_id: 7,
    )

    assert action_tasks.evaluate_effects.run("record-1") == {
        "evaluationId": "evaluation-1"
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
