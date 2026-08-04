from django.urls import path

from apps.advertising.views import (
    CampaignExportView,
    CampaignListView,
    SearchTermListView,
    TargetingListView,
)

urlpatterns = [
    path(
        "tenants/<str:tenant_id>/profiles/<str:profile_id>/campaigns/export",
        CampaignExportView.as_view(),
        name="advertising-campaign-export",
    ),
    path(
        "tenants/<str:tenant_id>/profiles/<str:profile_id>/campaigns",
        CampaignListView.as_view(),
        name="advertising-campaign-list",
    ),
    path(
        "tenants/<str:tenant_id>/profiles/<str:profile_id>/targeting",
        TargetingListView.as_view(),
        name="advertising-targeting-list",
    ),
    path(
        "tenants/<str:tenant_id>/profiles/<str:profile_id>/search-terms",
        SearchTermListView.as_view(),
        name="advertising-search-term-list",
    ),
]
