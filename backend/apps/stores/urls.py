from django.urls import path

from apps.stores.views import (
    ContextCapabilitiesView,
    CurrentContextView,
    MarketplaceOptionsView,
    ProfileOptionsView,
    StoreOptionsView,
    TenantOptionsView,
)

urlpatterns = [
    path("current", CurrentContextView.as_view(), name="context-current"),
    path("tenants", TenantOptionsView.as_view(), name="context-tenants"),
    path(
        "tenants/<str:tenant_id>/capabilities",
        ContextCapabilitiesView.as_view(),
        name="context-capabilities",
    ),
    path(
        "tenants/<str:tenant_id>/stores",
        StoreOptionsView.as_view(),
        name="context-stores",
    ),
    path(
        "tenants/<str:tenant_id>/stores/<str:store_id>/marketplaces",
        MarketplaceOptionsView.as_view(),
        name="context-marketplaces",
    ),
    path(
        "tenants/<str:tenant_id>/store-marketplaces/"
        "<str:store_marketplace_id>/profiles",
        ProfileOptionsView.as_view(),
        name="context-profiles",
    ),
]
