from django.urls import path

from apps.analytics.views import (
    DashboardView,
    SearchTermAnalyticsView,
    TargetingAnalyticsView,
)

urlpatterns = [
    path("dashboard", DashboardView.as_view()),
    path("targeting", TargetingAnalyticsView.as_view()),
    path("search-terms", SearchTermAnalyticsView.as_view()),
]

