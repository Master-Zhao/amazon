from django.urls import include, path

from api.v1.views import ConnectivityTestView, PlatformInfoView

urlpatterns = [
    path("", PlatformInfoView.as_view(), name="api-v1-root"),
    path("connectivity/", ConnectivityTestView.as_view(), name="connectivity-test"),
    path("auth/", include("apps.accounts.urls")),
    path("context/", include("apps.stores.urls")),
    path("access/", include("apps.permissions.urls")),
    path("access/", include("apps.tenants.urls")),
    path("permissions/", include("apps.permissions.urls")),
    path("reports/", include("apps.reports.urls")),
    path("advertising/", include("apps.advertising.urls")),
    path("products/", include("apps.products.urls")),
    path("analytics/", include("apps.analytics.urls")),
    path("analysis/", include("apps.agents.urls")),
    path("recommendations/", include("apps.recommendations.urls")),
    path("actions/", include("apps.actions.urls")),
    path("knowledge/", include("apps.knowledge.urls")),
    path("audit/", include("apps.audit.urls")),
    path("notifications/", include("apps.notifications.urls")),
]
