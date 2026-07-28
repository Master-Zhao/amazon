import uuid

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.actions.serializers import (
    DecisionSerializer,
    ExecutionRecordSerializer,
    PreviewCreateSerializer,
)
from apps.actions.services import (
    create_preview,
    decide_preview,
    record_execution,
    submit_preview,
)
from apps.core.pagination import page_spec, paginate_queryset
from apps.core.responses import api_response
from apps.actions.models import ActionPreview, ExecutionTask
from apps.permissions.services import authorize
from rest_framework.exceptions import ValidationError
from apps.stores.models import AdvertisingProfile


class PreviewCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OpenApiResponse(description="动作预览与执行列表")},
        tags=["actions"],
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
            from rest_framework.exceptions import NotFound

            raise NotFound("广告 Profile 不存在") from exc
        authorize(user=request.user, tenant_id=tenant_id, profile=profile)
        previews_query = (
            ActionPreview.objects.filter(
                tenant_id=tenant_id, profile=profile
            )
            .select_related("profile", "created_by")
            .prefetch_related(
                "versions",
                "approvals",
                "execution_task__items__records",
                "execution_task__evaluations",
            )
            .order_by("-created_at")
        )
        previews, pagination = paginate_queryset(previews_query, page_spec(request))
        return api_response(
            request,
            data={
                "items": [_preview_payload(item) for item in previews],
                "pagination": pagination,
            },
        )

    @extend_schema(request=PreviewCreateSerializer, responses={201: OpenApiResponse()}, tags=["actions"])
    def post(self, request):
        serializer = PreviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        preview = create_preview(
            request=request,
            tenant_id=data["tenant_id"],
            profile_id=data["profile_id"],
            recommendation_ids=data["recommendation_ids"],
            idempotency_key=request.headers.get("Idempotency-Key") or uuid.uuid4().hex,
        )
        return api_response(
            request, data={"preview_id": str(preview.pk), "status": preview.status}, status=201
        )


class PreviewSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: OpenApiResponse()}, tags=["actions"])
    def post(self, request, preview_id):
        preview = submit_preview(request=request, preview_id=preview_id)
        return api_response(request, data={"preview_id": str(preview.pk), "status": preview.status})


class PreviewDecisionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=DecisionSerializer, responses={200: OpenApiResponse()}, tags=["actions"])
    def post(self, request, preview_id):
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        preview = decide_preview(
            request=request,
            preview_id=preview_id,
            idempotency_key=request.headers.get("Idempotency-Key") or uuid.uuid4().hex,
            **serializer.validated_data,
        )
        return api_response(request, data={"preview_id": str(preview.pk), "status": preview.status})


class ExecutionRecordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ExecutionRecordSerializer, responses={201: OpenApiResponse()}, tags=["actions"])
    def post(self, request, item_id):
        serializer = ExecutionRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = record_execution(
            request=request,
            item_id=item_id,
            idempotency_key=request.headers.get("Idempotency-Key") or uuid.uuid4().hex,
            **{
                "result": serializer.validated_data["result"],
                "actual_value": serializer.validated_data["actual_value"],
                "executed_at": serializer.validated_data["executed_at"],
                "note": serializer.validated_data["note"],
                "evidence_file": serializer.validated_data.get("evidence"),
            },
        )
        return api_response(request, data={"record_id": str(record.pk)}, status=status.HTTP_201_CREATED)


def _preview_payload(preview):
    version = next(
        (item for item in preview.versions.all() if item.version == preview.current_version),
        None,
    )
    try:
        execution = preview.execution_task
    except ExecutionTask.DoesNotExist:
        execution = None
    return {
        "id": str(preview.pk),
        "status": preview.status,
        "current_version": preview.current_version,
        "version_lock": preview.version_lock,
        "created_by_id": str(preview.created_by_id),
        "created_at": preview.created_at,
        "version": (
            {
                "version": version.version,
                "items": version.items,
                "content_hash": version.content_hash,
                "frozen_at": version.frozen_at,
            }
            if version
            else None
        ),
        "approvals": [
            {
                "id": str(item.pk),
                "decision": item.decision,
                "actor_id": str(item.actor_id),
                "comment": item.comment,
                "created_at": item.created_at,
            }
            for item in preview.approvals.all()
        ],
        "execution": (
            {
                "id": str(execution.pk),
                "status": execution.status,
                "items": [
                    {
                        "id": str(item.pk),
                        "status": item.status,
                        "action": item.action,
                        "records": [
                            {
                                "id": str(record.pk),
                                "result": record.result,
                                "actual_value": record.actual_value,
                                "executed_at": record.executed_at,
                                "note": record.note,
                                "evidence_path": record.evidence_path,
                            }
                            for record in item.records.all()
                        ],
                    }
                    for item in execution.items.all()
                ],
                "evaluations": [
                    {
                        "id": str(item.pk),
                        "status": item.status,
                        "baseline": item.baseline,
                        "observed": item.observed,
                    }
                    for item in execution.evaluations.all()
                ],
            }
            if execution
            else None
        ),
    }
