import logging

from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.core.errors import ErrorCode
from apps.core.responses import request_id_for, response_envelope

logger = logging.getLogger(__name__)

_ERROR_CODE_BY_EXCEPTION = {
    exceptions.NotAuthenticated: ErrorCode.AUTHENTICATION_REQUIRED,
    exceptions.AuthenticationFailed: ErrorCode.AUTHENTICATION_REQUIRED,
    exceptions.PermissionDenied: ErrorCode.PERMISSION_DENIED,
    exceptions.NotFound: ErrorCode.RESOURCE_NOT_FOUND,
    exceptions.MethodNotAllowed: ErrorCode.METHOD_NOT_ALLOWED,
    exceptions.UnsupportedMediaType: ErrorCode.UNSUPPORTED_MEDIA_TYPE,
    exceptions.Throttled: ErrorCode.RATE_LIMITED,
    exceptions.ValidationError: ErrorCode.VALIDATION_ERROR,
}


def api_exception_handler(exc, context):
    request = context.get("request")
    request_id = request_id_for(request)
    handled = exception_handler(exc, context)

    if handled is None:
        logger.exception(
            "Unhandled API exception",
            extra={"request_id": request_id},
        )
        return Response(
            response_envelope(
                request_id=request_id,
                code=ErrorCode.INTERNAL_ERROR,
                message="服务器内部错误",
                data={"errors": {}},
            ),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    error_code = next(
        (
            code
            for exception_type, code in _ERROR_CODE_BY_EXCEPTION.items()
            if isinstance(exc, exception_type)
        ),
        ErrorCode.VALIDATION_ERROR,
    )
    message = "请求处理失败"
    if isinstance(handled.data, dict) and "detail" in handled.data:
        message = str(handled.data["detail"])

    return Response(
        response_envelope(
            request_id=request_id,
            code=error_code,
            message=message,
            data={"errors": handled.data},
        ),
        status=handled.status_code,
        headers=handled.headers,
    )
