from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import api_response
from apps.permissions.services import require_tenant_management
from apps.tenants.models import Team, TenantMembership
from apps.tenants.serializers import (
    AddTeamMemberSerializer,
    AssignRoleSerializer,
    CreateTeamSerializer,
    MembershipOptionSerializer,
    TeamOptionSerializer,
)
from apps.tenants.services import add_team_member, assign_role, create_team


class MembershipListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: MembershipOptionSerializer(many=True)},
        tags=["tenant-management"],
    )
    def get(self, request, tenant_id):
        manager = require_tenant_management(
            user=request.user,
            tenant_id=tenant_id,
        )
        data = [
            {
                "id": str(item.pk),
                "user_id": str(item.user_id),
                "email": item.user.email,
                "membership_role": item.membership_role,
                "is_active": item.is_active,
            }
            for item in TenantMembership.objects.filter(
                tenant=manager.tenant
            )
            .select_related("user")
            .order_by("user__email")
        ]
        return api_response(request, data=data)


class TeamListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: TeamOptionSerializer(many=True)},
        tags=["tenant-management"],
    )
    def get(self, request, tenant_id):
        manager = require_tenant_management(
            user=request.user,
            tenant_id=tenant_id,
        )
        data = [
            {
                "id": str(team.pk),
                "name": team.name,
                "member_ids": [
                    str(item.membership_id) for item in team.team_members.all()
                ],
            }
            for team in Team.objects.filter(
                tenant=manager.tenant,
                is_active=True,
            )
            .prefetch_related("team_members")
            .order_by("name")
        ]
        return api_response(request, data=data)

    @extend_schema(
        request=CreateTeamSerializer,
        responses={201: TeamOptionSerializer},
        tags=["tenant-management"],
    )
    def post(self, request, tenant_id):
        serializer = CreateTeamSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team = create_team(
            request=request,
            tenant_id=tenant_id,
            **serializer.validated_data,
        )
        return api_response(
            request,
            data={"id": str(team.pk), "name": team.name, "member_ids": []},
            status=status.HTTP_201_CREATED,
        )

class TeamMemberCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=AddTeamMemberSerializer,
        responses={201: None},
        tags=["tenant-management"],
    )
    def post(self, request, tenant_id, team_id):
        serializer = AddTeamMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        add_team_member(
            request=request,
            tenant_id=tenant_id,
            team_id=team_id,
            membership_id=serializer.validated_data["membership_id"],
        )
        return api_response(
            request,
            data={},
            message="Team 成员已保存",
            status=status.HTTP_201_CREATED,
        )


class MembershipRoleCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=AssignRoleSerializer,
        responses={201: None},
        tags=["tenant-management"],
    )
    def post(self, request, tenant_id):
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assign_role(
            request=request,
            tenant_id=tenant_id,
            membership_id=serializer.validated_data["membership_id"],
            role_id=serializer.validated_data["role_id"],
        )
        return api_response(
            request,
            data={},
            message="角色已分配",
            status=status.HTTP_201_CREATED,
        )
