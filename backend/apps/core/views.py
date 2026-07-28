from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.views import APIView

from apps.core.health import readiness_status
from apps.core.responses import api_response


class LiveHealthView(APIView):
    authentication_classes: list[type] = []
    permission_classes: list[type] = []

    @extend_schema(
        summary="Liveness probe",
        responses={200: OpenApiResponse(description="Django process is alive")},
        tags=["health"],
    )
    def get(self, request):
        return api_response(
            request,
            data={"status": "alive"},
            message="服务存活",
        )


class ReadyHealthView(APIView):
    authentication_classes: list[type] = []
    permission_classes: list[type] = []

    @extend_schema(
        summary="Readiness probe",
        responses={
            200: OpenApiResponse(description="Required dependencies are available"),
            503: OpenApiResponse(description="One or more dependencies are unavailable"),
        },
        tags=["health"],
    )
    def get(self, request):
        ready, dependencies = readiness_status()
        if ready:
            return api_response(
                request,
                data={"status": "ready", "dependencies": dependencies},
                message="服务就绪",
            )
        return api_response(
            request,
            data={"status": "not_ready", "dependencies": dependencies},
            message="服务尚未就绪",
            code="SERVICE_NOT_READY",
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
