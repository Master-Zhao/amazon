from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.core.pagination import page_spec, paginate_queryset
from apps.core.responses import api_response
from apps.permissions.services import authorize


class AuditLogListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiResponse(description="审计日志")}, tags=["audit"])
    def get(self, request):
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            raise ValidationError("缺少当前 Tenant")
        authorize(
            user=request.user, tenant_id=tenant_id, permission_code="audit.view"
        )
        logs_query = AuditLog.objects.filter(tenant_id=tenant_id).select_related("actor").order_by(
            "-created_at"
        )
        logs, pagination = paginate_queryset(
            logs_query, page_spec(request, default_page_size=100, max_page_size=200)
        )
        return api_response(
            request,
            data={
                "items": [
                    {
                        "id": str(item.pk),
                        "event": item.event,
                        "object_type": item.object_type,
                        "object_id": item.object_id,
                        "before": item.before,
                        "after": item.after,
                        "actor_id": str(item.actor_id) if item.actor_id else None,
                        "request_id": item.request_id,
                        "created_at": item.created_at,
                    }
                    for item in logs
                ],
                "pagination": pagination,
            },
        )
