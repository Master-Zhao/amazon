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
from apps.core.responses import api_response


class PreviewCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=PreviewCreateSerializer, responses={201: OpenApiResponse()}, tags=["actions"])
    def post(self, request):
        serializer = PreviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        preview = create_preview(
            request=request,
            tenant_id=data["tenantId"],
            profile_id=data["profileId"],
            recommendation_ids=data["recommendationIds"],
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
            idempotency_key=request.headers.get("Idempotency-Key", ""),
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
            idempotency_key=request.headers.get("Idempotency-Key", ""),
            **{
                "result": serializer.validated_data["result"],
                "actual_value": serializer.validated_data["actualValue"],
                "executed_at": serializer.validated_data["executedAt"],
                "note": serializer.validated_data["note"],
            },
        )
        return api_response(request, data={"record_id": str(record.pk)}, status=status.HTTP_201_CREATED)

