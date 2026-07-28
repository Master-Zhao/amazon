from django.urls import path

from apps.products.views import ProductListCreateView, ProductListingCreateView

urlpatterns = [
    path(
        "tenants/<str:tenant_id>",
        ProductListCreateView.as_view(),
        name="product-list-create",
    ),
    path(
        "tenants/<str:tenant_id>/<str:product_id>/listings",
        ProductListingCreateView.as_view(),
        name="product-listing-create",
    ),
]
