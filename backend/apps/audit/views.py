from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.audit.selectors import audit_logs_for_tenant
from apps.audit.serializers import AuditLogSerializer
from apps.core.responses import api_response


class AuditLogListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List append-only business audit events",
        parameters=[OpenApiParameter("event", str, required=False)],
        responses={200: AuditLogSerializer(many=True)},
        tags=["audit"],
    )
    def get(self, request, tenant_id):
        logs = audit_logs_for_tenant(
            user=request.user,
            tenant_id=tenant_id,
            event=request.query_params.get("event"),
        )
        return api_response(
            request,
            data=AuditLogSerializer(logs, many=True).data,
        )
