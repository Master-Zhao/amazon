from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.agents.models import AnalysisTask
from apps.agents.serializers import AnalysisCreateSerializer
from apps.agents.services import create_analysis
from apps.core.responses import api_response
from apps.permissions.services import authorize


class AnalysisCreateView(APIView):
    permission_classes = [IsAuthenticated]

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
            tenant_id=data["tenantId"],
            profile_id=data["profileId"],
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return api_response(
            request,
            data={"task_id": str(task.pk), "status": task.status},
            status=status.HTTP_202_ACCEPTED,
        )


class AnalysisDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiResponse(description="分析结果")}, tags=["analysis"])
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

