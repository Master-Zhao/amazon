from django.urls import path

from apps.actions.views import (
    ActionPreviewCreateView,
    ActionPreviewDecisionView,
    ActionPreviewListView,
    ActionPreviewSubmitView,
    ManualExecutionView,
)

urlpatterns = [
    path(
        "tenants/<str:tenant_id>/profiles/<str:profile_id>/previews",
        ActionPreviewListView.as_view(),
        name="action-preview-list",
    ),
    path(
        "tenants/<str:tenant_id>/recommendations/<str:recommendation_id>/previews",
        ActionPreviewCreateView.as_view(),
        name="action-preview-create",
    ),
    path(
        "tenants/<str:tenant_id>/previews/<str:preview_id>/submit",
        ActionPreviewSubmitView.as_view(),
        name="action-preview-submit",
    ),
    path(
        "tenants/<str:tenant_id>/previews/<str:preview_id>/decision",
        ActionPreviewDecisionView.as_view(),
        name="action-preview-decision",
    ),
    path(
        "tenants/<str:tenant_id>/previews/<str:preview_id>/executions",
        ManualExecutionView.as_view(),
        name="manual-execution-create",
    ),
]
