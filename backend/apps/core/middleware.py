import logging
import re
import uuid

from django.conf import settings

from apps.core.request_context import reset_request_id, set_request_id

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
access_logger = logging.getLogger("django.request")


class AccessControlAllowHeadersMiddleware:
    """Expose the accepted request headers on every backend response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Access-Control-Allow-Headers"] = ", ".join(
            settings.CORS_ALLOW_HEADERS
        )
        return response


def create_request_id() -> str:
    return f"req_{uuid.uuid4().hex}"


def normalize_request_id(candidate: str | None) -> str:
    if candidate and _VALID_REQUEST_ID.fullmatch(candidate):
        return candidate
    return create_request_id()


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
        request.request_id = request_id
        token = set_request_id(request_id)
        try:
            response = self.get_response(request)
            response[REQUEST_ID_HEADER] = request_id
            access_logger.info(
                "HTTP request completed",
                extra={
                    "event": "http_request_completed",
                    "request_id": request_id,
                    "http_method": request.method,
                    "http_path": request.path,
                    "status_code": response.status_code,
                },
            )
            return response
        finally:
            reset_request_id(token)
