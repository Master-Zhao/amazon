from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import api_response
from apps.reports.models import ImportTask
from apps.reports.selectors import task_for_user
from apps.reports.serializers import ReportUploadSerializer, TaskResponseSerializer
from apps.reports.services import create_upload_task, reprocess


class ReportUploadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="上传三类广告报表并创建异步导入任务",
        request=ReportUploadSerializer,
        responses={202: TaskResponseSerializer},
        tags=["reports"],
    )
    def post(self, request):
        serializer = ReportUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        task = create_upload_task(
            user=request.user,
            tenant_id=data["tenantId"],
            profile_id=data["profileId"],
            report_type=data["reportType"],
            uploaded_file=data["file"],
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return api_response(
            request,
            data={
                "task_id": str(task.pk),
                "status": task.status,
                "is_duplicate": task.upload.is_duplicate,
                "task_url": f"/api/v1/reports/tasks/{task.pk}",
            },
            message="导入任务已创建",
            status=status.HTTP_202_ACCEPTED,
        )


def _tenant_id(request):
    value = request.headers.get("X-Tenant-ID") or request.query_params.get("tenantId")
    if not value:
        raise ValidationError({"tenantId": "必须提供当前卖家空间"})
    return value


class ImportTaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="查看导入任务、批次计数和行级错误",
        responses={200: OpenApiResponse(description="导入任务详情")},
        tags=["reports"],
    )
    def get(self, request, task_id):
        return api_response(
            request,
            data=task_for_user(
                user=request.user, tenant_id=_tenant_id(request), task_id=task_id
            ),
        )


class ImportTaskReprocessView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="重处理历史 Upload 并创建新 Task/Batch",
        request=None,
        responses={202: TaskResponseSerializer},
        tags=["reports"],
    )
    def post(self, request, task_id):
        try:
            task = ImportTask.objects.select_related(
                "upload__profile__store_marketplace__store"
            ).get(pk=task_id)
        except ImportTask.DoesNotExist as exc:
            raise NotFound("导入任务不存在") from exc
        new_task = reprocess(
            user=request.user, tenant_id=_tenant_id(request), task=task
        )
        return api_response(
            request,
            data={
                "task_id": str(new_task.pk),
                "status": new_task.status,
                "is_duplicate": new_task.upload.is_duplicate,
                "task_url": f"/api/v1/reports/tasks/{new_task.pk}",
            },
            message="重处理任务已创建",
            status=status.HTTP_202_ACCEPTED,
        )
