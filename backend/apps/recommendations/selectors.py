from apps.permissions.models import ProfileAccessLevel
from apps.permissions.services import require_profile_scope
from apps.recommendations.models import Recommendation


def recommendations_for_profile(*, user, tenant_id, profile_id):
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="recommendations.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    recommendations = (
        Recommendation.objects.filter(
            tenant=scope.membership.tenant,
            profile=scope.profile,
        )
        .select_related("campaign", "agent_run")
        .prefetch_related("revisions")
        .order_by("-created_at")
    )
    return scope, recommendations
