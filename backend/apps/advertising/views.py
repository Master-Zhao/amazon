import csv
from io import StringIO

from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.advertising.selectors import (
    campaign_detail_page,
    campaign_rows,
    campaign_overview_page,
    create_remote_campaign,
    search_term_rows,
    targeting_rows,
    update_campaign_enabled_state,
)
from apps.advertising.serializers import (
    CampaignCreateResponseSerializer,
    CampaignCreateSerializer,
    CampaignDetailResponseSerializer,
    CampaignDetailQuerySerializer,
    CampaignEnabledUpdateResponseSerializer,
    CampaignEnabledUpdateSerializer,
    CampaignListQuerySerializer,
    CampaignOverviewResponseSerializer,
    CampaignRowSerializer,
    SearchTermRowSerializer,
    TargetingRowSerializer,
)
from apps.advertising.services import record_campaign_export
from apps.core.responses import api_response


class CampaignExportTooLarge(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "导出结果超过 10,000 行，请缩小筛选范围"
    default_code = "campaign_export_too_large"


def _csv_safe(value: object) -> str:
    rendered = "" if value is None else str(value)
    if rendered.startswith(("=", "+", "-", "@")):
        return f"'{rendered}"
    return rendered


def _money_amount(value: object) -> str:
    return str(value.get("amount", "")) if isinstance(value, dict) else ""


class CampaignListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="advertising_campaigns_list",
        summary="List read-only remote Sponsored Products Campaign performance",
        parameters=[CampaignListQuerySerializer],
        responses={200: CampaignOverviewResponseSerializer},
        tags=["advertising"],
    )
    def get(self, request, tenant_id, profile_id):
        overview_parameters = {
            "startDate",
            "endDate",
            "enabled",
            "status",
            "targetingType",
            "search",
            "metricFilters",
            "ordering",
            "page",
            "pageSize",
            "includeSummary",
        }
        if not overview_parameters.intersection(request.query_params):
            rows = campaign_rows(
                user=request.user,
                tenant_id=tenant_id,
                profile_id=profile_id,
            )
            return api_response(
                request,
                data=CampaignRowSerializer(rows, many=True).data,
            )
        query = CampaignListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        result = campaign_overview_page(
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
            query=query.validated_data,
        )
        return api_response(
            request,
            data=CampaignOverviewResponseSerializer(result).data,
        )

    @extend_schema(
        operation_id="advertising_campaigns_create",
        summary="Create one remote Campaign in SCM metadata",
        request=CampaignCreateSerializer,
        responses={201: CampaignCreateResponseSerializer},
        tags=["advertising"],
    )
    def post(self, request, tenant_id, profile_id):
        serializer = CampaignCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = create_remote_campaign(
            request=request,
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
            name=serializer.validated_data["name"],
            targeting_type=serializer.validated_data["targeting_type"],
            daily_budget=serializer.validated_data["daily_budget"],
            bidding_strategy=serializer.validated_data["bidding_strategy"],
            start_date=serializer.validated_data["start_date"],
            end_date=serializer.validated_data.get("end_date"),
            enabled=serializer.validated_data.get("enabled", True),
        )
        return api_response(
            request,
            data=CampaignCreateResponseSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )


class CampaignDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="advertising_campaigns_retrieve",
        summary="Retrieve one remote Campaign with composite daily trend",
        parameters=[CampaignDetailQuerySerializer],
        responses={200: CampaignDetailResponseSerializer},
        tags=["advertising"],
    )
    def get(self, request, tenant_id, profile_id, campaign_key):
        query = CampaignDetailQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        result = campaign_detail_page(
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
            campaign_key=campaign_key,
            start_date=query.validated_data.get("start_date"),
            end_date=query.validated_data.get("end_date"),
        )
        return api_response(
            request,
            data=CampaignDetailResponseSerializer(result).data,
        )


class CampaignEnabledUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="advertising_campaigns_update_enabled",
        summary="Update one remote Campaign enabled state in SCM metadata",
        request=CampaignEnabledUpdateSerializer,
        responses={200: CampaignEnabledUpdateResponseSerializer},
        tags=["advertising"],
    )
    def patch(self, request, tenant_id, profile_id, campaign_key):
        serializer = CampaignEnabledUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = update_campaign_enabled_state(
            request=request,
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
            campaign_key=campaign_key,
            enabled=serializer.validated_data["enabled"],
            start_date=serializer.validated_data.get("start_date"),
            end_date=serializer.validated_data.get("end_date"),
        )
        return api_response(
            request,
            data=CampaignEnabledUpdateResponseSerializer(result).data,
        )


class CampaignExportView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="advertising_campaigns_export",
        summary="Export the filtered read-only remote Campaign list as CSV",
        parameters=[CampaignListQuerySerializer],
        responses={(200, "text/csv"): bytes},
        tags=["advertising"],
    )
    def get(self, request, tenant_id, profile_id):
        query = CampaignListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        export_query = {
            **query.validated_data,
            "page": 1,
            "page_size": 10_001,
            "include_summary": False,
        }
        result = campaign_overview_page(
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
            query=export_query,
        )
        if result["pagination"]["total"] > 10_000:
            raise CampaignExportTooLarge()

        output = StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(
            [
                "广告活动名称",
                "广告活动代码",
                "投放类型",
                "状态",
                "竞价方案",
                "开始日期",
                "结束日期",
                "预算金额",
                "币种",
                "展示量",
                "搜索结果首页位置",
                "花费",
                "点击量",
                "CTR",
                "总成本",
                "购买量",
                "CPC",
                "ACoS",
                "CVR",
            ]
        )
        for item in result["items"]:
            metrics = item["metrics"]
            budget = item["daily_budget"]
            writer.writerow(
                [
                    _csv_safe(item["name"]),
                    _csv_safe(item["campaign_code"]),
                    item["targeting_type"],
                    item["status"],
                    item["bidding_strategy"],
                    item["start_date"] or "",
                    item["end_date"] or "",
                    _money_amount(budget),
                    budget.get("currency_code", "") if budget else result["meta"]["currency_code"],
                    metrics["impressions"],
                    metrics["top_of_search_share"] or "",
                    _money_amount(metrics["spend"]),
                    metrics["clicks"],
                    metrics["ctr"] or "",
                    _money_amount(metrics["total_cost"]),
                    metrics["orders"],
                    _money_amount(metrics["cpc"]),
                    metrics["acos"] or "",
                    metrics["cvr"] or "",
                ]
            )

        record_campaign_export(
            request=request,
            tenant_id=tenant_id,
            profile_id=profile_id,
            row_count=len(result["items"]),
        )
        dates = result["meta"]
        filename = (
            f"campaigns-{dates['start_date'] or 'latest'}-"
            f"{dates['end_date'] or 'latest'}.csv"
        )
        response = HttpResponse(
            "\ufeff" + output.getvalue(),
            content_type="text/csv; charset=utf-8",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Cache-Control"] = "no-store"
        return response


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
