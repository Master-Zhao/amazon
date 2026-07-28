from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.advertising.selectors import campaigns, search_terms, targeting
from apps.core.responses import api_response


class AdvertisingListView(APIView):
    permission_classes = [IsAuthenticated]
    selector = None

    @extend_schema(
        summary="查询导入后的广告对象",
        responses={200: OpenApiResponse(description="广告对象列表")},
        tags=["advertising"],
    )
    def get(self, request):
        tenant_id = request.headers.get("X-Tenant-ID")
        profile_id = request.query_params.get("profileId")
        if not tenant_id or not profile_id:
            raise ValidationError({"context": "tenantId/profileId 必填"})
        return api_response(
            request,
            data={"items": self.selector(request.user, tenant_id, profile_id)},
        )


class CampaignListView(AdvertisingListView):
    selector = staticmethod(campaigns)


class TargetingListView(AdvertisingListView):
    selector = staticmethod(targeting)


class SearchTermListView(AdvertisingListView):
    selector = staticmethod(search_terms)

