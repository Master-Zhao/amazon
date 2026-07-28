from django.urls import path

from apps.analytics.views import (
    AnalyticsConfigurationView,
    AnomalyRuleConfigurationView,
    CampaignMetricDetailView,
    CampaignMetricListView,
    DashboardView,
    SearchTermMetricListView,
    TargetingMetricListView,
    TargetAcosConfigurationView,
)

urlpatterns = [
    path(
        "tenants/<str:tenant_id>/profiles/<str:profile_id>/dashboard",
        DashboardView.as_view(),
        name="analytics-dashboard",
    ),
    path(
        "tenants/<str:tenant_id>/profiles/<str:profile_id>/campaigns",
        CampaignMetricListView.as_view(),
        name="campaign-metric-list",
    ),
    path(
        "tenants/<str:tenant_id>/profiles/<str:profile_id>/campaigns/"
        "<str:campaign_id>",
        CampaignMetricDetailView.as_view(),
        name="campaign-metric-detail",
    ),
    path(
        "tenants/<str:tenant_id>/profiles/<str:profile_id>/configuration",
        AnalyticsConfigurationView.as_view(),
        name="analytics-configuration",
    ),
    path(
        "tenants/<str:tenant_id>/profiles/<str:profile_id>/configuration/"
        "target-acos",
        TargetAcosConfigurationView.as_view(),
        name="analytics-target-acos-configuration",
    ),
    path(
        "tenants/<str:tenant_id>/profiles/<str:profile_id>/configuration/"
        "rules",
        AnomalyRuleConfigurationView.as_view(),
        name="analytics-rule-configuration",
    ),
    path(
        "tenants/<str:tenant_id>/profiles/<str:profile_id>/targeting",
        TargetingMetricListView.as_view(),
        name="targeting-metric-list",
    ),
    path(
        "tenants/<str:tenant_id>/profiles/<str:profile_id>/search-terms",
        SearchTermMetricListView.as_view(),
        name="search-term-metric-list",
    ),
]
