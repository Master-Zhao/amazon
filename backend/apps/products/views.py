from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import api_response
from apps.products.selectors import product_rows
from apps.products.serializers import (
    ProductCreateSerializer,
    ProductListingInputSerializer,
    ProductRowSerializer,
)
from apps.products.services import add_product_listing, create_product


class ProductListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List Tenant products with ASIN/SKU listings",
        responses={200: ProductRowSerializer(many=True)},
        tags=["products"],
    )
    def get(self, request, tenant_id):
        rows = product_rows(user=request.user, tenant_id=tenant_id)
        return api_response(
            request,
            data=ProductRowSerializer(rows, many=True).data,
        )

    @extend_schema(
        summary="Create a Tenant product and its first listing",
        request=ProductCreateSerializer,
        responses={201: ProductRowSerializer},
        tags=["products"],
    )
    def post(self, request, tenant_id):
        serializer = ProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = create_product(
            request=request,
            tenant_id=tenant_id,
            **serializer.validated_data,
        )
        row = next(
            item
            for item in product_rows(user=request.user, tenant_id=tenant_id)
            if item["id"] == str(product.pk)
        )
        return api_response(
            request,
            data=ProductRowSerializer(row).data,
            status=201,
        )


class ProductListingCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Add another StoreMarketplace SKU/ASIN listing to a product",
        request=ProductListingInputSerializer,
        responses={201: ProductRowSerializer},
        tags=["products"],
    )
    def post(self, request, tenant_id, product_id):
        serializer = ProductListingInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = add_product_listing(
            request=request,
            tenant_id=tenant_id,
            product_id=product_id,
            **serializer.validated_data,
        )
        row = next(
            item
            for item in product_rows(user=request.user, tenant_id=tenant_id)
            if item["id"] == str(product.pk)
        )
        return api_response(
            request,
            data=ProductRowSerializer(row).data,
            status=201,
        )
