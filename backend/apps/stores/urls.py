from django.urls import path

from apps.stores.views import (
    ProfileContextListView,
    StoreContextListView,
    StoreMarketplaceContextListView,
    TenantContextListView,
)

urlpatterns = [
    path("tenants", TenantContextListView.as_view(), name="context-tenants"),
    path(
        "tenants/<uuid:tenant_id>/stores",
        StoreContextListView.as_view(),
        name="context-stores",
    ),
    path(
        "tenants/<uuid:tenant_id>/stores/<uuid:store_id>/marketplaces",
        StoreMarketplaceContextListView.as_view(),
        name="context-marketplaces",
    ),
    path(
        "tenants/<uuid:tenant_id>/store-marketplaces/<uuid:store_marketplace_id>/profiles",
        ProfileContextListView.as_view(),
        name="context-profiles",
    ),
]

