from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.analytics.selectors import (
    analytics_configuration,
    campaign_detail,
    campaign_metric_rows,
    dashboard_rows,
    search_term_metric_rows,
    targeting_metric_rows,
)
from apps.analytics.serializers import (
    AnalyticsConfigurationSerializer,
    AnomalyRuleCreateSerializer,
    AnomalyRuleVersionSerializer,
    CampaignDetailSerializer,
    CampaignMetricRowSerializer,
    DashboardRowSerializer,
    SearchTermMetricRowSerializer,
    TargetingMetricRowSerializer,
    TargetAcosUpdateSerializer,
)
from apps.analytics.services import (
    create_anomaly_rule_version,
    set_target_acos,
)
from apps.core.responses import api_response


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get Campaign-grain dashboard groups without cross-currency totals",
        parameters=[
            OpenApiParameter("startDate", str, required=False),
            OpenApiParameter("endDate", str, required=False),
        ],
        responses={200: DashboardRowSerializer(many=True)},
        tags=["analytics"],
    )
    def get(self, request, tenant_id, profile_id):
        rows = dashboard_rows(
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
            start_date=request.query_params.get("startDate"),
            end_date=request.query_params.get("endDate"),
        )
        return api_response(
            request,
            data=DashboardRowSerializer(rows, many=True).data,
        )


class CampaignMetricListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List authoritative Campaign daily metrics and deterministic anomalies",
        parameters=[
            OpenApiParameter("startDate", str, required=False),
            OpenApiParameter("endDate", str, required=False),
        ],
        responses={200: CampaignMetricRowSerializer(many=True)},
        tags=["analytics"],
    )
    def get(self, request, tenant_id, profile_id):
        rows = campaign_metric_rows(
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
            start_date=request.query_params.get("startDate"),
            end_date=request.query_params.get("endDate"),
        )
        return api_response(
            request,
            data=CampaignMetricRowSerializer(rows, many=True).data,
        )


class CampaignMetricDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get Campaign detail and daily trend",
        parameters=[
            OpenApiParameter("startDate", str, required=False),
            OpenApiParameter("endDate", str, required=False),
        ],
        responses={200: CampaignDetailSerializer},
        tags=["analytics"],
    )
    def get(self, request, tenant_id, profile_id, campaign_id):
        result = campaign_detail(
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
            campaign_id=campaign_id,
            start_date=request.query_params.get("startDate"),
            end_date=request.query_params.get("endDate"),
        )
        return api_response(
            request,
            data=CampaignDetailSerializer(result).data,
        )


class AnalyticsConfigurationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get effective target ACOS and latest anomaly rule versions",
        responses={200: AnalyticsConfigurationSerializer},
        tags=["analytics"],
    )
    def get(self, request, tenant_id, profile_id):
        result = analytics_configuration(
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
        )
        return api_response(
            request,
            data=AnalyticsConfigurationSerializer(result).data,
        )


class TargetAcosConfigurationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Configure Tenant, Profile or Campaign target ACOS",
        request=TargetAcosUpdateSerializer,
        responses={200: AnalyticsConfigurationSerializer},
        tags=["analytics"],
    )
    def put(self, request, tenant_id, profile_id):
        serializer = TargetAcosUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        set_target_acos(
            request=request,
            tenant_id=tenant_id,
            profile_id=profile_id,
            **serializer.validated_data,
        )
        result = analytics_configuration(
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
        )
        return api_response(
            request,
            data=AnalyticsConfigurationSerializer(result).data,
        )


class AnomalyRuleConfigurationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Append a scoped anomaly rule version",
        request=AnomalyRuleCreateSerializer,
        responses={201: AnomalyRuleVersionSerializer},
        tags=["analytics"],
    )
    def post(self, request, tenant_id, profile_id):
        serializer = AnomalyRuleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rule = create_anomaly_rule_version(
            request=request,
            tenant_id=tenant_id,
            profile_id=profile_id,
            **serializer.validated_data,
        )
        return api_response(
            request,
            data=AnomalyRuleVersionSerializer(rule).data,
            status=201,
            message="Anomaly rule version created.",
        )


class TargetingMetricListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List authoritative Targeting daily metrics",
        parameters=[
            OpenApiParameter("startDate", str, required=False),
            OpenApiParameter("endDate", str, required=False),
        ],
        responses={200: TargetingMetricRowSerializer(many=True)},
        tags=["analytics"],
    )
    def get(self, request, tenant_id, profile_id):
        rows = targeting_metric_rows(
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
            start_date=request.query_params.get("startDate"),
            end_date=request.query_params.get("endDate"),
        )
        return api_response(
            request,
            data=TargetingMetricRowSerializer(rows, many=True).data,
        )


class SearchTermMetricListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List authoritative Search Term daily metrics",
        parameters=[
            OpenApiParameter("startDate", str, required=False),
            OpenApiParameter("endDate", str, required=False),
        ],
        responses={200: SearchTermMetricRowSerializer(many=True)},
        tags=["analytics"],
    )
    def get(self, request, tenant_id, profile_id):
        rows = search_term_metric_rows(
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
            start_date=request.query_params.get("startDate"),
            end_date=request.query_params.get("endDate"),
        )
        return api_response(
            request,
            data=SearchTermMetricRowSerializer(rows, many=True).data,
        )
