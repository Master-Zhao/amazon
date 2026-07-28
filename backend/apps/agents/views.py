from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.agents.models import AnalysisTask
from apps.agents.serializers import AnalysisCreateSerializer
from apps.agents.services import create_analysis
from apps.core.pagination import page_spec, paginate_queryset
from apps.core.responses import api_response
from apps.permissions.services import authorize
from apps.stores.models import AdvertisingProfile


class AnalysisCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="analysis_task_list",
        responses={200: OpenApiResponse(description="分析任务列表")},
        tags=["analysis"],
    )
    def get(self, request):
        tenant_id = request.headers.get("X-Tenant-ID")
        profile_id = request.query_params.get("profileId")
        if not tenant_id or not profile_id:
            raise NotFound("缺少当前 Tenant/Profile")
        try:
            profile = AdvertisingProfile.objects.select_related(
                "store_marketplace__store"
            ).get(pk=profile_id)
        except (AdvertisingProfile.DoesNotExist, ValueError) as exc:
            raise NotFound("广告 Profile 不存在") from exc
        authorize(
            user=request.user,
            tenant_id=tenant_id,
            permission_code="analytics.view",
            profile=profile,
        )
        tasks_query = AnalysisTask.objects.filter(
            tenant_id=tenant_id, profile=profile
        ).order_by("-created_at")
        tasks, pagination = paginate_queryset(tasks_query, page_spec(request))
        return api_response(
            request,
            data={
                "items": [
                    {
                        "task_id": str(task.pk),
                        "status": task.status,
                        "error": task.error,
                        "created_at": task.created_at,
                        "completed_at": task.completed_at,
                    }
                    for task in tasks
                ],
                "pagination": pagination,
            },
        )

    @extend_schema(
        request=AnalysisCreateSerializer,
        responses={202: OpenApiResponse(description="分析任务")},
        tags=["analysis"],
    )
    def post(self, request):
        serializer = AnalysisCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        task = create_analysis(
            user=request.user,
            tenant_id=data["tenant_id"],
            profile_id=data["profile_id"],
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return api_response(
            request,
            data={"task_id": str(task.pk), "status": task.status},
            status=status.HTTP_202_ACCEPTED,
        )


class AnalysisDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="analysis_task_retrieve",
        responses={200: OpenApiResponse(description="分析结果")},
        tags=["analysis"],
    )
    def get(self, request, task_id):
        try:
            task = AnalysisTask.objects.select_related("profile").prefetch_related("runs").get(
                pk=task_id
            )
        except AnalysisTask.DoesNotExist as exc:
            raise NotFound("分析任务不存在") from exc
        authorize(
            user=request.user,
            tenant_id=task.tenant_id,
            permission_code="analytics.view",
            profile=task.profile,
        )
        return api_response(
            request,
            data={
                "task_id": str(task.pk),
                "status": task.status,
                "result": task.result,
                "error": task.error,
                "runs": [
                    {"agent_code": run.agent_code, "status": run.status, "output": run.output}
                    for run in task.runs.all()
                ],
            },
        )
