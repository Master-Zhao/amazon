from rest_framework.exceptions import NotFound

from apps.permissions.models import ProfileAccessLevel
from apps.permissions.services import require_profile_scope
from apps.reports.models import ImportTask


def import_tasks_for_profile(*, user, tenant_id, profile_id):
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="reports.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    return ImportTask.objects.filter(
        upload__tenant=scope.membership.tenant,
        upload__profile=scope.profile,
    ).select_related(
        "upload",
        "reprocessed_from",
    ).order_by("-created_at")


def authorized_import_task(*, user, tenant_id, task_id) -> ImportTask:
    task = (
        ImportTask.objects.select_related(
            "upload__tenant",
            "upload__profile",
            "upload__duplicate_of",
            "reprocessed_from",
        )
        .filter(pk=task_id, upload__tenant_id=tenant_id)
        .first()
    )
    if task is None:
        raise NotFound("Import task does not exist in the current tenant scope.")
    require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=task.upload.profile_id,
        permission_code="reports.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    return task
