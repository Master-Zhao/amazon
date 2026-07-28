from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.advertising.models import Campaign
from apps.recommendations.models import Recommendation, RecommendationRevision

ALLOWED_ACTIONS = {
    "UPDATE_CAMPAIGN_BUDGET",
    "ENABLE_CAMPAIGN",
    "PAUSE_CAMPAIGN",
    "UPDATE_KEYWORD_BID",
    "ENABLE_KEYWORD",
    "PAUSE_KEYWORD",
    "UPDATE_TARGET_BID",
    "ENABLE_TARGET",
    "PAUSE_TARGET",
    "ADD_KEYWORD",
    "ADD_NEGATIVE_KEYWORD",
}


def validate_recommendation(*, task, item):
    if item.get("actionType") not in ALLOWED_ACTIONS:
        raise ValidationError("不支持的建议动作")
    if item.get("riskLevel") not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValidationError("风险等级无效")
    if item.get("objectType") == "CAMPAIGN":
        try:
            campaign = Campaign.objects.get(
                pk=item["objectId"], profile=task.profile
            )
        except (Campaign.DoesNotExist, ValueError, KeyError) as exc:
            raise ValidationError("建议对象越出授权 Profile") from exc
        if item["actionType"] == "UPDATE_CAMPAIGN_BUDGET":
            before = item.get("beforeValue", {}).get("budget")
            after = item.get("afterValue", {}).get("budget")
            if str(campaign.daily_budget) != str(before):
                raise ValidationError("建议 beforeValue 已漂移")
            try:
                next_value = Decimal(str(after))
            except (InvalidOperation, TypeError) as exc:
                raise ValidationError("预算金额无效") from exc
            if next_value <= 0 or next_value > Decimal("1000000"):
                raise ValidationError("预算超出允许范围")
    return item


@transaction.atomic
def persist_recommendations(*, task, items):
    created = []
    for item in items:
        validate_recommendation(task=task, item=item)
        recommendation, was_created = Recommendation.objects.get_or_create(
            analysis_task=task,
            action_type=item["actionType"],
            object_id=item["objectId"],
            defaults={
                "tenant": task.tenant,
                "profile": task.profile,
                "object_type": item["objectType"],
                "before_value": item["beforeValue"],
                "after_value": item["afterValue"],
                "reason": item["reason"],
                "evidence": item["evidence"],
                "risk_level": item["riskLevel"],
            },
        )
        if was_created:
            RecommendationRevision.objects.create(
                recommendation=recommendation, version=1, content=item
            )
        created.append(recommendation)
    return created

