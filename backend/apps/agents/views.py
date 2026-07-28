from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.agents.selectors import agent_runs_for_profile
from apps.agents.serializers import AgentRunSerializer
from apps.agents.services import create_agent_run
from apps.core.responses import api_response


class AgentRunListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List AI analysis runs for an AdvertisingProfile",
        responses={200: AgentRunSerializer(many=True)},
        tags=["analysis"],
    )
    def get(self, request, tenant_id, profile_id):
        _, runs = agent_runs_for_profile(
            user=request.user,
            tenant_id=tenant_id,
            profile_id=profile_id,
        )
        return api_response(
            request,
            data=AgentRunSerializer(runs, many=True).data,
        )

    @extend_schema(
        summary="Queue a four-agent analysis using MockLLMProvider",
        request=None,
        responses={202: AgentRunSerializer},
        tags=["analysis"],
    )
    def post(self, request, tenant_id, profile_id):
        run = create_agent_run(
            request=request,
            tenant_id=tenant_id,
            profile_id=profile_id,
        )
        return api_response(
            request,
            data=AgentRunSerializer(run).data,
            message="Analysis run queued.",
            status=202,
        )
