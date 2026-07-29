from django.urls import path

from apps.recommendations.views import (
    RecommendationAcceptView,
    RecommendationDismissView,
    RecommendationListView,
    RecommendationReviseView,
)

urlpatterns = [
    path(
        "tenants/<str:tenant_id>/profiles/<str:profile_id>",
        RecommendationListView.as_view(),
        name="recommendation-list",
    ),
    path(
        "tenants/<str:tenant_id>/<str:recommendation_id>/accept",
        RecommendationAcceptView.as_view(),
        name="recommendation-accept",
    ),
    path(
        "tenants/<str:tenant_id>/<str:recommendation_id>/dismiss",
        RecommendationDismissView.as_view(),
        name="recommendation-dismiss",
    ),
    path(
        "tenants/<str:tenant_id>/<str:recommendation_id>/revisions",
        RecommendationReviseView.as_view(),
        name="recommendation-revise",
    ),
]
