from django.urls import path

from apps.permissions.views import (
    PermissionListView,
    RoleAssignmentView,
    RoleListCreateView,
    UserProfileGrantView,
    UserStoreGrantView,
)

urlpatterns = [
    path("", PermissionListView.as_view(), name="permission-list"),
    path("roles", RoleListCreateView.as_view(), name="role-list-create"),
    path(
        "roles/<uuid:role_id>/assignments",
        RoleAssignmentView.as_view(),
        name="role-assignment",
    ),
    path(
        "stores/<uuid:store_id>/user-grants",
        UserStoreGrantView.as_view(),
        name="user-store-grant",
    ),
    path(
        "profiles/<uuid:profile_id>/user-grants",
        UserProfileGrantView.as_view(),
        name="user-profile-grant",
    ),
]
