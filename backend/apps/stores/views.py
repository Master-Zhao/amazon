from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import api_response
from apps.stores.selectors import (
    context_capabilities,
    marketplace_options,
    profile_options,
    store_options,
    tenant_options,
)
from apps.stores.serializers import (
    ContextCapabilitiesSerializer,
    ProfileOptionSerializer,
    StoreMarketplaceOptionSerializer,
    StoreOptionSerializer,
    TenantOptionSerializer,
)


class TenantOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="获取当前用户可进入的卖家空间",
        responses={200: TenantOptionSerializer(many=True)},
        tags=["tenant-context"],
    )
    def get(self, request):
        return api_response(request, data=tenant_options(request.user))


class StoreOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="获取卖家空间内可访问的店铺",
        responses={200: StoreOptionSerializer(many=True)},
        tags=["tenant-context"],
    )
    def get(self, request, tenant_id):
        return api_response(
            request,
            data=store_options(user=request.user, tenant_id=tenant_id),
        )


class MarketplaceOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="获取店铺的 Marketplace 关联",
        responses={200: StoreMarketplaceOptionSerializer(many=True)},
        tags=["tenant-context"],
    )
    def get(self, request, tenant_id, store_id):
        return api_response(
            request,
            data=marketplace_options(
                user=request.user,
                tenant_id=tenant_id,
                store_id=store_id,
            ),
        )


class ProfileOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="获取 StoreMarketplace 下可访问的 AdvertisingProfile",
        responses={200: ProfileOptionSerializer(many=True)},
        tags=["tenant-context"],
    )
    def get(self, request, tenant_id, store_marketplace_id):
        return api_response(
            request,
            data=profile_options(
                user=request.user,
                tenant_id=tenant_id,
                store_marketplace_id=store_marketplace_id,
            ),
        )


class ContextCapabilitiesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="获取当前卖家空间的功能权限和 Membership 角色",
        responses={200: ContextCapabilitiesSerializer},
        tags=["tenant-context"],
    )
    def get(self, request, tenant_id):
        return api_response(
            request,
            data=context_capabilities(user=request.user, tenant_id=tenant_id),
        )
