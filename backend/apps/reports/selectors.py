from rest_framework.exceptions import NotFound

from apps.permissions.services import authorize
from apps.reports.models import ImportTask


def task_for_user(*, user, tenant_id, task_id):
    try:
        task = (
            ImportTask.objects.select_related("upload__profile__store_marketplace__store")
            .prefetch_related("batch__row_errors")
            .get(pk=task_id)
        )
    except (ImportTask.DoesNotExist, ValueError) as exc:
        raise NotFound("导入任务不存在") from exc
    authorize(
        user=user,
        tenant_id=tenant_id,
        permission_code="reports.view",
        profile=task.upload.profile,
    )
    batch = getattr(task, "batch", None)
    return {
        "task_id": str(task.pk),
        "upload_id": str(task.upload_id),
        "report_type": task.upload.report_type,
        "status": task.status,
        "is_duplicate": task.upload.is_duplicate,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "error_code": task.error_code,
        "batch": (
            {
                "id": str(batch.pk),
                "total_rows": batch.total_rows,
                "succeeded_rows": batch.succeeded_rows,
                "failed_rows": batch.failed_rows,
                "errors": [
                    {
                        "row_number": error.row_number,
                        "code": error.code,
                        "field": error.field,
                        "message": error.message,
                    }
                    for error in batch.row_errors.all()
                ],
            }
            if batch
            else None
        ),
    }

