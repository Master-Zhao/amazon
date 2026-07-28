from django.http import FileResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import api_response
from apps.reports.selectors import (
    authorized_import_task,
    import_tasks_for_profile,
)
from apps.reports.serializers import (
    ImportRowErrorSerializer,
    ImportTaskSerializer,
    ReportUploadRequestSerializer,
)
from apps.reports.services import create_report_import, reprocess_import
from integrations.storage.local import LocalFileStorage


class ReportUploadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Upload a report and enqueue its asynchronous import",
        request=ReportUploadRequestSerializer,
        responses={202: ImportTaskSerializer},
        tags=["reports"],
    )
    def post(self, request, tenant_id, profile_id):
        serializer = ReportUploadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = create_report_import(
            request=request,
            tenant_id=tenant_id,
            profile_id=profile_id,
            report_type=serializer.validated_data["report_type"],
            uploaded_file=serializer.validated_data["file"],
        )
        return api_response(
            request,
            data=ImportTaskSerializer(task).data,
            message="Report import queued.",
            status=202,
        )


class ImportTaskListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List import tasks for an AdvertisingProfile",
        responses={200: ImportTaskSerializer(many=True)},
        tags=["reports"],
    )
    def get(self, request, tenant_id, profile_id):
        tasks = import_tasks_for_profile(
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
        )
        return api_response(
            request,
            data=ImportTaskSerializer(tasks, many=True).data,
        )


class ImportTaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get import task status and counters",
        responses={200: ImportTaskSerializer},
        tags=["reports"],
    )
    def get(self, request, tenant_id, task_id):
        task = authorized_import_task(
            user=request.user,
            tenant_id=tenant_id,
            task_id=task_id,
        )
        return api_response(request, data=ImportTaskSerializer(task).data)


class ImportTaskErrorListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List row-level import errors",
        responses={200: ImportRowErrorSerializer(many=True)},
        tags=["reports"],
    )
    def get(self, request, tenant_id, task_id):
        task = authorized_import_task(
            user=request.user,
            tenant_id=tenant_id,
            task_id=task_id,
        )
        errors = task.row_errors.order_by("row_number", "id")
        return api_response(
            request,
            data=ImportRowErrorSerializer(errors, many=True).data,
        )


class ImportTaskReprocessView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Create a new append-only import attempt from an existing upload",
        request=None,
        responses={202: ImportTaskSerializer},
        tags=["reports"],
    )
    def post(self, request, tenant_id, task_id):
        task = reprocess_import(
            request=request,
            tenant_id=tenant_id,
            task_id=task_id,
        )
        return api_response(
            request,
            data=ImportTaskSerializer(task).data,
            message="Report reprocessing queued.",
            status=202,
        )


class ImportTaskSourceDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Download the authorized original report source",
        responses={(200, "application/octet-stream"): OpenApiTypes.BINARY},
        tags=["reports"],
    )
    def get(self, request, tenant_id, task_id):
        task = authorized_import_task(
            user=request.user,
            tenant_id=tenant_id,
            task_id=task_id,
        )
        stream = LocalFileStorage().open(key=task.upload.storage_key)
        return FileResponse(
            stream,
            as_attachment=True,
            filename=task.upload.original_filename,
            content_type=task.upload.content_type or "application/octet-stream",
        )
