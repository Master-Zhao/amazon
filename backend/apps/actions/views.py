from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.actions.selectors import action_previews_for_profile
from apps.actions.serializers import (
    ActionPreviewSerializer,
    ApprovalDecisionRequestSerializer,
    EffectEvaluationRequestSerializer,
    EffectEvaluationSerializer,
    ManualExecutionRequestSerializer,
    ReturnedVersionRequestSerializer,
)
from apps.actions.services import (
    create_returned_preview_version,
    create_action_preview,
    decide_action_preview,
    evaluate_action_preview_effect,
    record_manual_execution,
    submit_action_preview,
    withdraw_action_preview,
)
from apps.core.responses import api_response


class ActionPreviewListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List Action Previews, approvals and manual execution records",
        responses={200: ActionPreviewSerializer(many=True)},
        tags=["actions"],
    )
    def get(self, request, tenant_id, profile_id):
        _, previews = action_previews_for_profile(
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
        )
        return api_response(
            request,
            data=ActionPreviewSerializer(previews, many=True).data,
        )


class ActionPreviewCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Create an immutable Action Preview version from a Recommendation",
        request=None,
        responses={201: ActionPreviewSerializer},
        tags=["actions"],
    )
    def post(self, request, tenant_id, recommendation_id):
        preview = create_action_preview(
            request=request,
            tenant_id=tenant_id,
            recommendation_id=recommendation_id,
        )
        return api_response(
            request,
            data=ActionPreviewSerializer(preview).data,
            message="Action Preview created.",
            status=201,
        )


class ActionPreviewSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Submit a DRAFT Action Preview for single-level approval",
        request=None,
        responses={200: ActionPreviewSerializer},
        tags=["actions"],
    )
    def post(self, request, tenant_id, preview_id):
        preview = submit_action_preview(
            request=request,
            tenant_id=tenant_id,
            preview_id=preview_id,
        )
        return api_response(
            request,
            data=ActionPreviewSerializer(preview).data,
            message="Action Preview submitted.",
        )


class ActionPreviewWithdrawView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Withdraw a creator-owned Action Preview",
        request=None,
        responses={200: ActionPreviewSerializer},
        tags=["actions"],
    )
    def post(self, request, tenant_id, preview_id):
        preview = withdraw_action_preview(
            request=request,
            tenant_id=tenant_id,
            preview_id=preview_id,
        )
        return api_response(
            request,
            data=ActionPreviewSerializer(preview).data,
            message="Action Preview withdrawn.",
        )


class ReturnedPreviewVersionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Append a revised immutable version after RETURNED",
        request=ReturnedVersionRequestSerializer,
        responses={201: ActionPreviewSerializer},
        tags=["actions"],
    )
    def post(self, request, tenant_id, preview_id):
        serializer = ReturnedVersionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        preview = create_returned_preview_version(
            request=request,
            tenant_id=tenant_id,
            preview_id=preview_id,
            **serializer.validated_data,
        )
        return api_response(
            request,
            data=ActionPreviewSerializer(preview).data,
            message="Action Preview version created.",
            status=201,
        )


class ActionPreviewDecisionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Record one append-only approval decision",
        request=ApprovalDecisionRequestSerializer,
        responses={200: ActionPreviewSerializer},
        tags=["approvals"],
    )
    def post(self, request, tenant_id, preview_id):
        serializer = ApprovalDecisionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        preview, _ = decide_action_preview(
            request=request,
            tenant_id=tenant_id,
            preview_id=preview_id,
            **serializer.validated_data,
        )
        return api_response(
            request,
            data=ActionPreviewSerializer(preview).data,
            message="Approval decision recorded.",
        )


class ManualExecutionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Backfill one manual Amazon console execution result",
        request=ManualExecutionRequestSerializer,
        responses={201: ActionPreviewSerializer},
        tags=["executions"],
    )
    def post(self, request, tenant_id, preview_id):
        serializer = ManualExecutionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        values.setdefault("note", "")
        values.setdefault("evidence_metadata", {})
        preview, _ = record_manual_execution(
            request=request,
            tenant_id=tenant_id,
            preview_id=preview_id,
            **values,
        )
        return api_response(
            request,
            data=ActionPreviewSerializer(preview).data,
            message="Manual execution result recorded.",
            status=201,
        )


class EffectEvaluationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Append a basic post-execution effect evaluation",
        request=EffectEvaluationRequestSerializer,
        responses={201: EffectEvaluationSerializer},
        tags=["executions"],
    )
    def post(self, request, tenant_id, preview_id):
        serializer = EffectEvaluationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        values.setdefault("observed", {})
        evaluation = evaluate_action_preview_effect(
            request=request,
            tenant_id=tenant_id,
            preview_id=preview_id,
            **values,
        )
        return api_response(
            request,
            data=EffectEvaluationSerializer(evaluation).data,
            message="Effect evaluation recorded.",
            status=201,
        )
