from django.urls import path

from apps.actions.views import (
    ExecutionRecordView,
    PreviewCreateView,
    PreviewDecisionView,
    PreviewSubmitView,
)

urlpatterns = [
    path("previews", PreviewCreateView.as_view()),
    path("previews/<uuid:preview_id>/submit", PreviewSubmitView.as_view()),
    path("previews/<uuid:preview_id>/decisions", PreviewDecisionView.as_view()),
    path("execution-items/<uuid:item_id>/records", ExecutionRecordView.as_view()),
]
