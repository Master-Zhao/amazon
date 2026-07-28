from apps.audit.models import AuditLog


def append_audit_log(
    *,
    request,
    event: str,
    tenant=None,
    actor=None,
    object_type: str = "",
    object_id: str = "",
    task_id: str = "",
    before_data: dict | None = None,
    after_data: dict | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    return AuditLog.objects.create(
        tenant=tenant,
        actor=actor,
        event=event,
        object_type=object_type,
        object_id=str(object_id) if object_id else "",
        request_id=getattr(request, "request_id", "system"),
        task_id=task_id,
        before_data=before_data or {},
        after_data=after_data or {},
        metadata=metadata or {},
    )
