from django.urls import path

from apps.audit.views import AuditLogListView

urlpatterns = [
    path(
        "tenants/<str:tenant_id>",
        AuditLogListView.as_view(),
        name="audit-log-list",
    ),
]
