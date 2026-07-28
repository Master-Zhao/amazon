from rest_framework.exceptions import NotFound

from apps.actions.models import ActionPreview
from apps.permissions.models import ProfileAccessLevel
from apps.permissions.services import require_profile_scope


def action_previews_for_profile(*, user, tenant_id, profile_id):
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="recommendations.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    previews = (
        ActionPreview.objects.filter(
            tenant=scope.membership.tenant,
            profile=scope.profile,
        )
        .select_related(
            "recommendation_revision__recommendation__campaign",
            "created_by",
            "submitted_by",
        )
        .prefetch_related(
            "versions",
            "approval_records__decided_by",
            "execution_records__recorded_by",
            "execution_records__effect_evaluations",
        )
        .order_by("-created_at")
    )
    return scope, previews


def authorized_action_preview(*, user, tenant_id, preview_id) -> ActionPreview:
    preview = (
        ActionPreview.objects.select_related("tenant", "profile")
        .filter(pk=preview_id, tenant_id=tenant_id)
        .first()
    )
    if preview is None:
        raise NotFound("Action Preview does not exist in the current tenant scope.")
    require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=preview.profile_id,
        permission_code="recommendations.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    return preview
