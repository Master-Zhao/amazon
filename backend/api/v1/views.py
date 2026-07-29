from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.views import APIView

from apps.core.responses import api_response
from apps.tenants.models import Tenant


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


class ConnectivityTestView(APIView):
    authentication_classes: list[type] = []
    permission_classes: list[type] = []
    throttle_classes: list[type] = []

    @extend_schema(
        summary="前后端连通性测试",
        description="无需认证，直接从数据库读取 Tenant 列表，用于验证前端→API→数据库→返回→渲染全链路。",
        responses={200: OpenApiResponse(description="Tenant 列表与数据库记录数")},
        tags=["connectivity"],
    )
    def get(self, request):
        tenants = Tenant.objects.all().order_by("pk")
        data = [
            {
                "id": str(t.pk),
                "name": t.name,
                "tenant_type": t.tenant_type,
                "target_acos": str(t.target_acos) if t.target_acos is not None else None,
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat(),
            }
            for t in tenants
        ]
        return api_response(
            request,
            data={"total": tenants.count(), "tenants": data},
            message="连通性测试：Tenant 数据已从数据库读取",
        )
