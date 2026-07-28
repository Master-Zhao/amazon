from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.advertising.selectors import (
    campaign_rows,
    search_term_rows,
    targeting_rows,
)
from apps.advertising.serializers import (
    CampaignRowSerializer,
    SearchTermRowSerializer,
    TargetingRowSerializer,
)
from apps.core.responses import api_response


class CampaignListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List normalized Sponsored Products Campaign entities",
        responses={200: CampaignRowSerializer(many=True)},
        tags=["advertising"],
    )
    def get(self, request, tenant_id, profile_id):
        rows = campaign_rows(
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
        )
        return api_response(
            request,
            data=CampaignRowSerializer(rows, many=True).data,
        )


class TargetingListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List normalized Keyword and Product Target entities",
        responses={200: TargetingRowSerializer(many=True)},
        tags=["advertising"],
    )
    def get(self, request, tenant_id, profile_id):
        rows = targeting_rows(
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
        )
        return api_response(
            request,
            data=TargetingRowSerializer(rows, many=True).data,
        )


class SearchTermListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List normalized customer Search Term entities",
        responses={200: SearchTermRowSerializer(many=True)},
        tags=["advertising"],
    )
    def get(self, request, tenant_id, profile_id):
        rows = search_term_rows(
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
        )
        return api_response(
            request,
            data=SearchTermRowSerializer(rows, many=True).data,
        )
