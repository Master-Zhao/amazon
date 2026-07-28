import re

import pytest
from rest_framework.test import APIClient

from apps.core.request_context import current_request_id


@pytest.mark.django_db
def test_request_id_is_generated_and_returned_in_header_and_body():
    response = APIClient().get("/api/v1/")

    request_id = response.headers["X-Request-ID"]
    assert re.fullmatch(r"req_[0-9a-f]{32}", request_id)
    assert response.json()["requestId"] == request_id


@pytest.mark.django_db
def test_valid_request_id_is_propagated():
    response = APIClient().get(
        "/api/v1/",
        HTTP_X_REQUEST_ID="req_client_123",
    )

    assert response.headers["X-Request-ID"] == "req_client_123"
    assert response.json()["requestId"] == "req_client_123"


@pytest.mark.django_db
def test_invalid_request_id_is_replaced():
    response = APIClient().get(
        "/api/v1/",
        HTTP_X_REQUEST_ID="invalid request id with spaces",
    )

    assert response.headers["X-Request-ID"].startswith("req_")
    assert response.headers["X-Request-ID"] != "invalid request id with spaces"


@pytest.mark.django_db
def test_request_context_is_cleared_between_requests():
    client = APIClient()

    first = client.get("/api/v1/", HTTP_X_REQUEST_ID="req_first")
    assert first.json()["requestId"] == "req_first"
    assert current_request_id() == "system"

    second = client.get("/api/v1/", HTTP_X_REQUEST_ID="req_second")
    assert second.json()["requestId"] == "req_second"
    assert current_request_id() == "system"
