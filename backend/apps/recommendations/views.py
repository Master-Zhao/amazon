from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import api_response
from apps.recommendations.selectors import recommendations_for_profile
from apps.recommendations.serializers import (
    DismissRequestSerializer,
    RecommendationSerializer,
    ReviseRequestSerializer,
)
from apps.recommendations.services import (
    accept_recommendation,
    dismiss_recommendation,
    revise_recommendation,
)


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


class RecommendationAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Accept an ACTIVE recommendation",
        request=None,
        responses={200: RecommendationSerializer},
        tags=["recommendations"],
    )
    def post(self, request, tenant_id, recommendation_id):
        recommendation = accept_recommendation(
            request=request,
            tenant_id=tenant_id,
            recommendation_id=recommendation_id,
        )
        return api_response(
            request,
            data=RecommendationSerializer(recommendation).data,
            message="建议已接受。",
        )


class RecommendationDismissView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Dismiss an ACTIVE or ACCEPTED recommendation",
        request=DismissRequestSerializer,
        responses={200: RecommendationSerializer},
        tags=["recommendations"],
    )
    def post(self, request, tenant_id, recommendation_id):
        serializer = DismissRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recommendation = dismiss_recommendation(
            request=request,
            tenant_id=tenant_id,
            recommendation_id=recommendation_id,
            reason=serializer.validated_data.get("reason", ""),
        )
        return api_response(
            request,
            data=RecommendationSerializer(recommendation).data,
            message="建议已拒绝。",
        )


class RecommendationReviseView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Revise an ACTIVE or ACCEPTED recommendation with a new revision",
        request=ReviseRequestSerializer,
        responses={200: RecommendationSerializer},
        tags=["recommendations"],
    )
    def post(self, request, tenant_id, recommendation_id):
        serializer = ReviseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recommendation = revise_recommendation(
            request=request,
            tenant_id=tenant_id,
            recommendation_id=recommendation_id,
            **serializer.validated_data,
        )
        return api_response(
            request,
            data=RecommendationSerializer(recommendation).data,
            message="建议已修订。",
        )
