from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import api_response
from apps.recommendations.selectors import recommendations_for_profile
from apps.recommendations.serializers import RecommendationSerializer


class RecommendationListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List validated structured Recommendations",
        responses={200: RecommendationSerializer(many=True)},
        tags=["recommendations"],
    )
    def get(self, request, tenant_id, profile_id):
        _, recommendations = recommendations_for_profile(
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
        )
        return api_response(
            request,
            data=RecommendationSerializer(recommendations, many=True).data,
        )
