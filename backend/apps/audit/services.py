from apps.audit.models import AuditLog


def append_audit(*, request, tenant, event, object_type, object_id, before=None, after=None):
    return AuditLog.objects.create(
        tenant=tenant,
        actor=request.user if getattr(request, "user", None) and request.user.is_authenticated else None,
        event=event,
        object_type=object_type,
        object_id=str(object_id),
        before=before or {},
        after=after or {},
        request_id=getattr(request, "request_id", "system"),
    )

