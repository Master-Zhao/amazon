import uuid

from django.db import models

from apps.agents.models import AnalysisTask
from apps.stores.models import AdvertisingProfile
from apps.tenants.models import Tenant


class Recommendation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT)
    profile = models.ForeignKey(AdvertisingProfile, on_delete=models.PROTECT)
    analysis_task = models.ForeignKey(
        AnalysisTask, on_delete=models.PROTECT, related_name="recommendations"
    )
    status = models.CharField(max_length=16, default="OPEN")
    action_type = models.CharField(max_length=64)
    object_type = models.CharField(max_length=64)
    object_id = models.CharField(max_length=128)
    before_value = models.JSONField(default=dict)
    after_value = models.JSONField(default=dict)
    reason = models.TextField()
    evidence = models.JSONField(default=list)
    risk_level = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_recommendation"
        constraints = [
            models.UniqueConstraint(
                fields=["analysis_task", "action_type", "object_id"],
                name="ai_recommendation_task_action_obj_uniq",
            )
        ]


class RecommendationRevision(models.Model):
    recommendation = models.ForeignKey(
        Recommendation, on_delete=models.PROTECT, related_name="revisions"
    )
    version = models.PositiveIntegerField()
    content = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_recommendation_revision"
        constraints = [
            models.UniqueConstraint(
                fields=["recommendation", "version"],
                name="ai_recommendation_revision_uniq",
            )
        ]

