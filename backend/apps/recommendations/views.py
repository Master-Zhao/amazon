from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.pagination import page_spec, paginate_queryset
from apps.core.responses import api_response
from apps.permissions.services import authorize
from apps.recommendations.models import Recommendation
from apps.stores.models import AdvertisingProfile


class RecommendationListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OpenApiResponse(description="建议列表")},
        tags=["recommendations"],
    )
    def get(self, request):
        tenant_id = request.headers.get("X-Tenant-ID")
        profile_id = request.query_params.get("profileId")
        if not tenant_id or not profile_id:
            raise ValidationError("缺少当前 Tenant/Profile")
        try:
            profile = AdvertisingProfile.objects.select_related(
                "store_marketplace__store"
            ).get(pk=profile_id)
        except (AdvertisingProfile.DoesNotExist, ValueError) as exc:
            raise NotFound("广告 Profile 不存在") from exc
        authorize(
            user=request.user,
            tenant_id=tenant_id,
            permission_code="recommendations.view",
            profile=profile,
        )
        items_query = Recommendation.objects.filter(
            tenant_id=tenant_id, profile=profile
        ).order_by("-created_at")
        items, pagination = paginate_queryset(items_query, page_spec(request))
        return api_response(
            request,
            data={
                "items": [
                    {
                        "id": str(item.pk),
                        "action_type": item.action_type,
                        "object_type": item.object_type,
                        "object_id": item.object_id,
                        "before_value": item.before_value,
                        "after_value": item.after_value,
                        "reason": item.reason,
                        "evidence": item.evidence,
                        "risk_level": item.risk_level,
                    }
                    for item in items
                ],
                "pagination": pagination,
            },
        )
