import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_openapi_schema_can_be_generated():
    response = APIClient().get("/api/schema/", HTTP_ACCEPT="application/json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Amazon Ads Optimizer API"
    assert "/health/live" in schema["paths"]
    assert "/health/ready" in schema["paths"]
    assert "/api/v1/" in schema["paths"]
    assert "/api/v1/auth/login" in schema["paths"]
    assert "/api/v1/auth/refresh" in schema["paths"]
    assert "/api/v1/auth/logout" in schema["paths"]
    assert "/api/v1/auth/me" in schema["paths"]
