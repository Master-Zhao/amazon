from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory

from apps.core.exceptions import api_exception_handler
from apps.core.responses import api_response


def test_unified_success_response_uses_internal_snake_case():
    request = APIRequestFactory().get("/")
    request.request_id = "req_test"

    response = api_response(
        request,
        data={"service_status": "available"},
        message="ok",
    )

    assert response.data == {
        "code": "SUCCESS",
        "message": "ok",
        "data": {"service_status": "available"},
        "request_id": "req_test",
    }


def test_unified_exception_response_keeps_stable_error_code():
    request = APIRequestFactory().post("/")
    request.request_id = "req_error"

    response = api_exception_handler(
        ValidationError({"invalid_field": ["required"]}),
        {"request": request, "view": object()},
    )

    assert response.status_code == 400
    assert response.data["code"] == "VALIDATION_ERROR"
    assert response.data["request_id"] == "req_error"
    assert response.data["data"]["errors"] == {"invalid_field": ["required"]}
