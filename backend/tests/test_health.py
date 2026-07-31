import io
import logging
import json
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.core.logging import JsonLogFormatter


@pytest.mark.django_db
def test_liveness_does_not_call_readiness_dependencies():
    client = APIClient()
    with patch("apps.core.views.readiness_status") as readiness:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["data"] == {"status": "alive"}
    readiness.assert_not_called()


@pytest.mark.django_db
def test_every_backend_response_declares_x_token_as_allowed_header():
    response = APIClient().get("/health/live")

    assert response.status_code == 200
    allowed_headers = {
        item.strip().lower()
        for item in response.headers["Access-Control-Allow-Headers"].split(",")
    }
    assert "x-token" in allowed_headers


@pytest.mark.django_db
def test_readiness_returns_success_when_dependencies_are_available():
    client = APIClient()
    with patch(
        "apps.core.views.readiness_status",
        return_value=(
            True,
            {
                "database": "available",
                "redis": "available",
                "configuration": "available",
            },
        ),
    ):
        response = client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "SUCCESS"
    assert body["data"]["status"] == "ready"


@pytest.mark.django_db
def test_readiness_returns_503_without_leaking_dependency_details():
    client = APIClient()
    with patch(
        "apps.core.views.readiness_status",
        return_value=(
            False,
            {
                "database": "unavailable",
                "redis": "available",
                "configuration": "missing:DB_PASSWORD",
            },
        ),
    ):
        response = client.get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "SERVICE_NOT_READY"
    assert body["data"]["status"] == "not_ready"
    serialized = response.content.decode()
    assert "password=" not in serialized.lower()
    assert "traceback" not in serialized.lower()


@pytest.mark.django_db
def test_redis_failure_returns_503_and_logs_same_request_id_without_secret(settings):
    settings.REDIS_URL = "redis://user:never-log-this-password@redis.internal:6379/0"
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLogFormatter())
    logger = logging.getLogger("apps.core.health")
    logger.addHandler(handler)
    request_id = "req_ready_redis_failure"

    try:
        with (
            patch("apps.core.health.check_database", return_value=(True, "available")),
            patch(
                "apps.core.health.check_required_configuration",
                return_value=(True, "available"),
            ),
            patch(
                "apps.core.health.redis.Redis.from_url",
                side_effect=ValueError(settings.REDIS_URL),
            ),
        ):
            response = APIClient().get(
                "/health/ready", HTTP_X_REQUEST_ID=request_id
            )
    finally:
        logger.removeHandler(handler)

    assert response.status_code == 503
    assert response.headers["X-Request-ID"] == request_id
    assert response.json()["requestId"] == request_id
    log_lines = [json.loads(line) for line in stream.getvalue().splitlines()]
    redis_log = next(
        line for line in log_lines if line.get("dependency") == "redis"
    )
    assert redis_log["level"] == "WARNING"
    assert redis_log["event"] == "readiness_check_failed"
    assert redis_log["requestId"] == request_id
    serialized_log = stream.getvalue()
    assert "never-log-this-password" not in serialized_log
    assert settings.REDIS_URL not in serialized_log
