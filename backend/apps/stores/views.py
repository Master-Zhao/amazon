from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import api_response
from apps.stores.serializers import (
    ProfileContextResponseSerializer,
    StoreContextResponseSerializer,
    StoreMarketplaceContextResponseSerializer,
    TenantContextResponseSerializer,
)
from apps.stores.selectors import (
    profiles_for,
    store_marketplaces_for,
    stores_for,
    tenant_contexts_for,
)


class TenantContextListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="获取当前用户可访问卖家空间",
        responses={200: TenantContextResponseSerializer},
        tags=["context"],
    )
    def get(self, request):
        return api_response(request, data={"items": tenant_contexts_for(request.user)})


class StoreContextListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="获取卖家空间可访问店铺",
        responses={200: StoreContextResponseSerializer},
        tags=["context"],
    )
    def get(self, request, tenant_id):
        return api_response(
            request, data={"items": stores_for(user=request.user, tenant_id=tenant_id)}
        )


class StoreMarketplaceContextListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="获取店铺站点范围",
        responses={200: StoreMarketplaceContextResponseSerializer},
        tags=["context"],
    )
    def get(self, request, tenant_id, store_id):
        return api_response(
            request,
            data={
                "items": store_marketplaces_for(
                    user=request.user, tenant_id=tenant_id, store_id=store_id
                )
            },
        )


class ProfileContextListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="获取站点范围内可访问广告 Profile",
        responses={200: ProfileContextResponseSerializer},
        tags=["context"],
    )
    def get(self, request, tenant_id, store_marketplace_id):
        return api_response(
            request,
            data={
                "items": profiles_for(
                    user=request.user,
                    tenant_id=tenant_id,
                    store_marketplace_id=store_marketplace_id,
                )
            },
        )
