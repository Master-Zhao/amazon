from django.urls import path

from apps.agents.views import AgentRunListCreateView

urlpatterns = [
    path(
        "tenants/<str:tenant_id>/profiles/<str:profile_id>/runs",
        AgentRunListCreateView.as_view(),
        name="agent-run-list-create",
    ),
]
