from django.urls import path

from apps.agents.views import AnalysisCreateView, AnalysisDetailView

urlpatterns = [
    path("tasks", AnalysisCreateView.as_view()),
    path("tasks/<uuid:task_id>", AnalysisDetailView.as_view()),
]

