from django.db import models

from apps.advertising.models import Campaign
from apps.agents.models import AgentRun
from apps.core.models import AppendOnlyModel
from apps.stores.models import AdvertisingProfile
from apps.tenants.models import Tenant


class RecommendationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUPERSEDED = "SUPERSEDED", "Superseded"
    ACCEPTED = "ACCEPTED", "Accepted"
    DISMISSED = "DISMISSED", "Dismissed"


class ActionType(models.TextChoices):
    UPDATE_CAMPAIGN_BUDGET = "UPDATE_CAMPAIGN_BUDGET", "Update Campaign budget"
    SET_CAMPAIGN_STATE = "SET_CAMPAIGN_STATE", "Pause or enable Campaign"
    UPDATE_KEYWORD_BID = "UPDATE_KEYWORD_BID", "Update Keyword bid"
    SET_KEYWORD_STATE = "SET_KEYWORD_STATE", "Pause or enable Keyword"
    UPDATE_PRODUCT_TARGET_BID = (
        "UPDATE_PRODUCT_TARGET_BID",
        "Update Product Target bid",
    )
    SET_PRODUCT_TARGET_STATE = (
        "SET_PRODUCT_TARGET_STATE",
        "Pause or enable Product Target",
    )
    CREATE_KEYWORD = "CREATE_KEYWORD", "Create Keyword"
    CREATE_NEGATIVE_KEYWORD = "CREATE_NEGATIVE_KEYWORD", "Create Negative Keyword"


class Recommendation(models.Model):
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="recommendations",
    )
    profile = models.ForeignKey(
        AdvertisingProfile,
        on_delete=models.PROTECT,
        related_name="recommendations",
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.PROTECT,
        related_name="recommendations",
    )
    agent_run = models.ForeignKey(
        AgentRun,
        on_delete=models.PROTECT,
        related_name="recommendations",
    )
    action_type = models.CharField(max_length=64, choices=ActionType.choices)
    status = models.CharField(
        max_length=16,
        choices=RecommendationStatus.choices,
        default=RecommendationStatus.ACTIVE,
    )
    current_revision_number = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_recommendation"
        constraints = [
            models.UniqueConstraint(
                fields=["agent_run", "campaign", "action_type"],
                name="ai_recommendation_run_object_action_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["tenant", "profile", "status", "-created_at"],
                name="ai_recommend_scope_status_idx",
            )
        ]


class RecommendationRevision(AppendOnlyModel):
    recommendation = models.ForeignKey(
        Recommendation,
        on_delete=models.PROTECT,
        related_name="revisions",
    )
    revision_number = models.PositiveIntegerField()
    schema_version = models.CharField(max_length=32)
    action_type = models.CharField(max_length=64, choices=ActionType.choices)
    object_type = models.CharField(max_length=64)
    object_id = models.CharField(max_length=128)
    before_value = models.JSONField(default=dict)
    after_value = models.JSONField(default=dict)
    reason = models.CharField(max_length=1000)
    evidence = models.JSONField(default=list)
    risk_level = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_recommendation_revision"
        constraints = [
            models.UniqueConstraint(
                fields=["recommendation", "revision_number"],
                name="ai_recommendation_revision_uniq",
            )
        ]


class LLMInvocation(AppendOnlyModel):
    agent_run = models.ForeignKey(
        AgentRun,
        on_delete=models.PROTECT,
        related_name="llm_invocations",
    )
    provider_code = models.CharField(max_length=64)
    agent_code = models.CharField(max_length=32)
    request_payload = models.JSONField(default=dict)
    response_payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_llm_invocation"
