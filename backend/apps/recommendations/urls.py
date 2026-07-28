from django.urls import path

from apps.recommendations.views import RecommendationListView

urlpatterns = [
    path(
        "tenants/<str:tenant_id>/profiles/<str:profile_id>",
        RecommendationListView.as_view(),
        name="recommendation-list",
    ),
]
