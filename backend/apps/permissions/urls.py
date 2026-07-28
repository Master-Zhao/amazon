from django.urls import path

from apps.permissions.views import (
    PermissionListView,
    ProfileAccessGrantView,
    RoleCopyView,
    RoleDetailView,
    RoleListCreateView,
    StoreAccessGrantView,
)

urlpatterns = [
    path(
        "tenants/<str:tenant_id>/permissions",
        PermissionListView.as_view(),
        name="permission-list",
    ),
    path(
        "tenants/<str:tenant_id>/roles",
        RoleListCreateView.as_view(),
        name="role-list-create",
    ),
    path(
        "tenants/<str:tenant_id>/roles/<str:role_id>",
        RoleDetailView.as_view(),
        name="role-detail",
    ),
    path(
        "tenants/<str:tenant_id>/roles/<str:role_id>/copy",
        RoleCopyView.as_view(),
        name="role-copy",
    ),
    path(
        "tenants/<str:tenant_id>/store-access",
        StoreAccessGrantView.as_view(),
        name="store-access-grant",
    ),
    path(
        "tenants/<str:tenant_id>/profile-access",
        ProfileAccessGrantView.as_view(),
        name="profile-access-grant",
    ),
]
