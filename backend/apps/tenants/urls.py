from django.urls import path

from apps.tenants.views import (
    MembershipListView,
    MembershipRoleCreateView,
    TeamListCreateView,
    TeamMemberCreateView,
)

urlpatterns = [
    path(
        "tenants/<str:tenant_id>/members",
        MembershipListView.as_view(),
        name="tenant-members",
    ),
    path(
        "tenants/<str:tenant_id>/teams",
        TeamListCreateView.as_view(),
        name="tenant-teams",
    ),
    path(
        "tenants/<str:tenant_id>/teams/<str:team_id>/members",
        TeamMemberCreateView.as_view(),
        name="tenant-team-members",
    ),
    path(
        "tenants/<str:tenant_id>/member-roles",
        MembershipRoleCreateView.as_view(),
        name="tenant-member-roles",
    ),
]
