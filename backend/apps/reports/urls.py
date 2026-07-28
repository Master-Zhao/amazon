from django.urls import path

from apps.reports.views import (
    ImportTaskDetailView,
    ImportTaskReprocessView,
    ReportUploadView,
)

urlpatterns = [
    path("uploads", ReportUploadView.as_view(), name="report-upload"),
    path("tasks/<uuid:task_id>", ImportTaskDetailView.as_view(), name="import-task"),
    path(
        "tasks/<uuid:task_id>/reprocess",
        ImportTaskReprocessView.as_view(),
        name="import-task-reprocess",
    ),
]

