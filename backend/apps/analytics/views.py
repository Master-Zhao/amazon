from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.analytics.selectors import dashboard, search_term_metrics, targeting_metrics
from apps.core.responses import api_response


class AnalyticsView(APIView):
    permission_classes = [IsAuthenticated]
    selector = None

    @extend_schema(
        summary="查询独立权威粒度广告指标",
        responses={200: OpenApiResponse(description="指标与异常")},
        tags=["analytics"],
    )
    def get(self, request):
        tenant_id = request.headers.get("X-Tenant-ID")
        profile_id = request.query_params.get("profileId")
        if not tenant_id or not profile_id:
            raise ValidationError({"context": "tenantId/profileId 必填"})
        return api_response(
            request, data=self.selector(request.user, tenant_id, profile_id)
        )


class DashboardView(AnalyticsView):
    selector = staticmethod(dashboard)


class TargetingAnalyticsView(AnalyticsView):
    selector = staticmethod(targeting_metrics)


class SearchTermAnalyticsView(AnalyticsView):
    selector = staticmethod(search_term_metrics)

