from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.views import APIView

from apps.core.responses import api_response


class PlatformInfoView(APIView):
    authentication_classes: list[type] = []
    permission_classes: list[type] = []

    @extend_schema(
        summary="Platform API information",
        responses={200: OpenApiResponse(description="Phase 1 platform information")},
        tags=["platform"],
    )
    def get(self, request):
        return api_response(
            request,
            data={
                "service_name": "amazon-ads-optimizer",
                "version": settings.APP_VERSION,
                "git_commit": settings.GIT_COMMIT,
                "build_time": settings.BUILD_TIME,
                "business_capabilities": "not_implemented",
            },
            message="平台基础接口可用",
        )
