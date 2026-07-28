from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import api_response
from apps.permissions.models import ProfileAccessLevel
from apps.permissions.selectors import permission_options, role_options
from apps.permissions.serializers import (
    CopyRoleSerializer,
    CreateRoleSerializer,
    PermissionOptionSerializer,
    ProfileAccessGrantSerializer,
    RoleOptionSerializer,
    StoreAccessGrantSerializer,
)
from apps.permissions.services import (
    copy_role,
    create_custom_role,
    deactivate_custom_role,
    grant_profile_access,
    grant_store_access,
)


class PermissionListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: PermissionOptionSerializer(many=True)},
        tags=["permissions"],
    )
    def get(self, request, tenant_id):
        return api_response(
            request,
            data=permission_options(user=request.user, tenant_id=tenant_id),
        )


class RoleListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: RoleOptionSerializer(many=True)},
        tags=["permissions"],
    )
    def get(self, request, tenant_id):
        return api_response(
            request,
            data=role_options(user=request.user, tenant_id=tenant_id),
        )

    @extend_schema(
        request=CreateRoleSerializer,
        responses={201: RoleOptionSerializer},
        tags=["permissions"],
    )
    def post(self, request, tenant_id):
        serializer = CreateRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = create_custom_role(
            request=request,
            tenant_id=tenant_id,
            name=serializer.validated_data["name"],
            code=serializer.validated_data["code"],
            permission_codes=serializer.validated_data["permission_codes"],
        )
        return api_response(
            request,
            data={"id": str(role.pk), "name": role.name, "code": role.code},
            status=status.HTTP_201_CREATED,
        )


class RoleCopyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CopyRoleSerializer,
        responses={201: RoleOptionSerializer},
        tags=["permissions"],
    )
    def post(self, request, tenant_id, role_id):
        serializer = CopyRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = copy_role(
            request=request,
            tenant_id=tenant_id,
            source_role_id=role_id,
            **serializer.validated_data,
        )
        return api_response(
            request,
            data={"id": str(role.pk), "name": role.name, "code": role.code},
            status=status.HTTP_201_CREATED,
        )


class RoleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={204: None}, tags=["permissions"])
    def delete(self, request, tenant_id, role_id):
        deactivate_custom_role(
            request=request,
            tenant_id=tenant_id,
            role_id=role_id,
        )
        return api_response(request, data={}, message="角色已停用")


class StoreAccessGrantView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=StoreAccessGrantSerializer,
        responses={201: None},
        tags=["permissions"],
    )
    def post(self, request, tenant_id):
        serializer = StoreAccessGrantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        grant_store_access(
            request=request,
            tenant_id=tenant_id,
            store_id=serializer.validated_data["store_id"],
            user_id=serializer.validated_data.get("user_id"),
            team_id=serializer.validated_data.get("team_id"),
        )
        return api_response(
            request,
            data={},
            message="Store 权限已保存",
            status=status.HTTP_201_CREATED,
        )


class ProfileAccessGrantView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ProfileAccessGrantSerializer,
        responses={201: None},
        tags=["permissions"],
    )
    def post(self, request, tenant_id):
        serializer = ProfileAccessGrantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        grant_profile_access(
            request=request,
            tenant_id=tenant_id,
            profile_id=serializer.validated_data["profile_id"],
            access_level=int(
                ProfileAccessLevel[
                    serializer.validated_data["access_level"]
                ]
            ),
            user_id=serializer.validated_data.get("user_id"),
            team_id=serializer.validated_data.get("team_id"),
        )
        return api_response(
            request,
            data={},
            message="Profile 权限已保存",
            status=status.HTTP_201_CREATED,
        )
