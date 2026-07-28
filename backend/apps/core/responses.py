from typing import Any

from rest_framework.response import Response


def request_id_for(request) -> str:
    return getattr(request, "request_id", "system")


def response_envelope(
    *,
    request_id: str,
    code: str,
    message: str,
    data: Any,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "data": data,
        "request_id": request_id,
    }


def api_response(
    request,
    *,
    data: Any = None,
    message: str = "操作成功",
    code: str = "SUCCESS",
    status: int = 200,
) -> Response:
    return Response(
        response_envelope(
            request_id=request_id_for(request),
            code=code,
            message=message,
            data={} if data is None else data,
        ),
        status=status,
    )
