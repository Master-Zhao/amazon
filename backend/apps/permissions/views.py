from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import api_response
from apps.permissions.models import Permission, Role
from apps.permissions.serializers import (
    AssignmentResponseSerializer,
    PermissionListResponseSerializer,
    RoleAssignmentSerializer,
    RoleCreateSerializer,
    RoleListResponseSerializer,
    RoleResponseSerializer,
    UserProfileGrantSerializer,
    UserStoreGrantSerializer,
)
from apps.permissions.services import (
    assign_role,
    authorize,
    create_role,
    grant_user_profile_access,
    grant_user_store_access,
)
from apps.stores.models import AdvertisingProfile, AmazonStore
from apps.tenants.models import Tenant


def _tenant(tenant_id):
    try:
        return Tenant.objects.get(pk=tenant_id, is_active=True)
    except Tenant.DoesNotExist as exc:
        raise NotFound("卖家空间不存在") from exc


def _role_data(role):
    return {
        "id": str(role.pk),
        "tenant_id": str(role.tenant_id) if role.tenant_id else None,
        "code": role.code,
        "name": role.name,
        "is_system": role.is_system,
        "permission_codes": sorted(role.permissions.values_list("code", flat=True)),
    }


class PermissionListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="获取固定功能权限目录",
        responses={200: PermissionListResponseSerializer},
        tags=["permissions"],
    )
    def get(self, request):
        return api_response(
            request,
            data={
                "items": list(
                    Permission.objects.order_by("code").values("code", "name", "description")
                )
            },
        )


class RoleListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="获取系统和当前卖家空间角色",
        responses={200: RoleListResponseSerializer},
        tags=["permissions"],
    )
    def get(self, request):
        tenant_id = request.query_params.get("tenantId")
        if not tenant_id:
            raise ValidationError({"tenantId": "必填"})
        authorize(user=request.user, tenant_id=tenant_id)
        roles = Role.objects.filter(Q(tenant_id=tenant_id) | Q(is_system=True)).prefetch_related(
            "permissions"
        )
        return api_response(request, data={"items": [_role_data(role) for role in roles]})

    @extend_schema(
        summary="创建 Tenant 自定义角色",
        request=RoleCreateSerializer,
        responses={201: RoleResponseSerializer},
        tags=["permissions"],
    )
    def post(self, request):
        serializer = RoleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            role = create_role(
                actor=request.user,
                tenant=_tenant(data["tenant_id"]),
                code=data["code"],
                name=data["name"],
                permission_codes=data["permission_codes"],
            )
        except ValueError as exc:
            raise ValidationError({"permissionCodes": str(exc)}) from exc
        return api_response(request, data=_role_data(role), status=201, message="角色已创建")


class RoleAssignmentView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="给 Tenant 成员分配角色",
        request=RoleAssignmentSerializer,
        responses={201: AssignmentResponseSerializer},
        tags=["permissions"],
    )
    def post(self, request, role_id):
        serializer = RoleAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            role = Role.objects.get(pk=role_id)
        except Role.DoesNotExist as exc:
            raise NotFound("角色不存在") from exc
        assignment = assign_role(
            actor=request.user,
            tenant=_tenant(data["tenant_id"]),
            role=role,
            user_id=data["user_id"],
        )
        return api_response(
            request,
            data={"id": str(assignment.pk)},
            status=201,
            message="角色已分配",
        )


class UserStoreGrantView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="给 Tenant 成员授予店铺范围",
        request=UserStoreGrantSerializer,
        responses={201: AssignmentResponseSerializer},
        tags=["permissions"],
    )
    def post(self, request, store_id):
        serializer = UserStoreGrantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            store = AmazonStore.objects.select_related("tenant").get(pk=store_id)
        except AmazonStore.DoesNotExist as exc:
            raise NotFound("店铺不存在") from exc
        grant = grant_user_store_access(
            actor=request.user,
            tenant=_tenant(data["tenant_id"]),
            store=store,
            user_id=data["user_id"],
        )
        return api_response(
            request, data={"id": str(grant.pk)}, status=201, message="店铺范围已授权"
        )


class UserProfileGrantView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="给 Tenant 成员授予 Profile 操作等级",
        request=UserProfileGrantSerializer,
        responses={201: AssignmentResponseSerializer},
        tags=["permissions"],
    )
    def post(self, request, profile_id):
        serializer = UserProfileGrantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            profile = AdvertisingProfile.objects.select_related(
                "store_marketplace__store__tenant"
            ).get(pk=profile_id)
        except AdvertisingProfile.DoesNotExist as exc:
            raise NotFound("广告 Profile 不存在") from exc
        grant = grant_user_profile_access(
            actor=request.user,
            tenant=_tenant(data["tenant_id"]),
            profile=profile,
            user_id=data["user_id"],
            level=data["level"],
        )
        return api_response(
            request, data={"id": str(grant.pk)}, status=201, message="Profile 已授权"
        )
