from django.urls import path

from apps.reports.views import (
    ImportTaskDetailView,
    ImportTaskErrorListView,
    ImportTaskListView,
    ImportTaskReprocessView,
    ImportTaskSourceDownloadView,
    ReportUploadView,
)

urlpatterns = [
    path(
        "tenants/<str:tenant_id>/profiles/<str:profile_id>/uploads",
        ReportUploadView.as_view(),
        name="report-upload",
    ),
    path(
        "tenants/<str:tenant_id>/profiles/<str:profile_id>/tasks",
        ImportTaskListView.as_view(),
        name="report-import-task-list",
    ),
    path(
        "tenants/<str:tenant_id>/tasks/<str:task_id>",
        ImportTaskDetailView.as_view(),
        name="report-import-task-detail",
    ),
    path(
        "tenants/<str:tenant_id>/tasks/<str:task_id>/errors",
        ImportTaskErrorListView.as_view(),
        name="report-import-task-errors",
    ),
    path(
        "tenants/<str:tenant_id>/tasks/<str:task_id>/reprocess",
        ImportTaskReprocessView.as_view(),
        name="report-import-task-reprocess",
    ),
    path(
        "tenants/<str:tenant_id>/tasks/<str:task_id>/source",
        ImportTaskSourceDownloadView.as_view(),
        name="report-import-source-download",
    ),
]
