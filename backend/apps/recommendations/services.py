from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.advertising.models import (
    AdGroup,
    Campaign,
    EntityState,
    Keyword,
    MatchType,
    ProductTarget,
)
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

STATE_ACTIONS = {
    "ENABLE_CAMPAIGN": ("CAMPAIGN", Campaign, "profile", EntityState.ENABLED),
    "PAUSE_CAMPAIGN": ("CAMPAIGN", Campaign, "profile", EntityState.PAUSED),
    "ENABLE_KEYWORD": (
        "KEYWORD",
        Keyword,
        "ad_group__campaign__profile",
        EntityState.ENABLED,
    ),
    "PAUSE_KEYWORD": (
        "KEYWORD",
        Keyword,
        "ad_group__campaign__profile",
        EntityState.PAUSED,
    ),
    "ENABLE_TARGET": (
        "PRODUCT_TARGET",
        ProductTarget,
        "ad_group__campaign__profile",
        EntityState.ENABLED,
    ),
    "PAUSE_TARGET": (
        "PRODUCT_TARGET",
        ProductTarget,
        "ad_group__campaign__profile",
        EntityState.PAUSED,
    ),
}

BID_ACTIONS = {
    "UPDATE_KEYWORD_BID": (
        "KEYWORD",
        Keyword,
        "ad_group__campaign__profile",
    ),
    "UPDATE_TARGET_BID": (
        "PRODUCT_TARGET",
        ProductTarget,
        "ad_group__campaign__profile",
    ),
}


def _object_for_profile(*, model, profile_path, task, item):
    try:
        return model.objects.get(
            pk=item["objectId"],
            **{profile_path: task.profile},
        )
    except (model.DoesNotExist, ValueError, KeyError) as exc:
        raise ValidationError("建议对象越出授权 Profile") from exc


def _positive_decimal(value, field):
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValidationError(f"{field} 金额无效") from exc
    if parsed <= 0 or parsed > Decimal("1000000"):
        raise ValidationError(f"{field} 超出允许范围")
    return parsed


def _same_decimal(current, proposed):
    try:
        return Decimal(str(current)) == Decimal(str(proposed))
    except (InvalidOperation, TypeError):
        return False


def validate_recommendation(*, task, item):
    action_type = item.get("actionType")
    if action_type not in ALLOWED_ACTIONS:
        raise ValidationError("不支持的建议动作")
    if item.get("riskLevel") not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValidationError("风险等级无效")
    before = item.get("beforeValue") or {}
    after = item.get("afterValue") or {}

    if action_type == "UPDATE_CAMPAIGN_BUDGET":
        if item.get("objectType") != "CAMPAIGN":
            raise ValidationError("动作与对象类型不匹配")
        campaign = _object_for_profile(
            model=Campaign, profile_path="profile", task=task, item=item
        )
        if not _same_decimal(campaign.daily_budget, before.get("budget")):
            raise ValidationError("建议 beforeValue 已漂移")
        _positive_decimal(after.get("budget"), "预算")
    elif action_type in STATE_ACTIONS:
        object_type, model, profile_path, target_state = STATE_ACTIONS[action_type]
        if item.get("objectType") != object_type:
            raise ValidationError("动作与对象类型不匹配")
        instance = _object_for_profile(
            model=model, profile_path=profile_path, task=task, item=item
        )
        if before.get("state") != instance.state:
            raise ValidationError("建议 beforeValue 已漂移")
        if after.get("state") != target_state or instance.state == target_state:
            raise ValidationError("状态转换无效")
    elif action_type in BID_ACTIONS:
        object_type, model, profile_path = BID_ACTIONS[action_type]
        if item.get("objectType") != object_type:
            raise ValidationError("动作与对象类型不匹配")
        instance = _object_for_profile(
            model=model, profile_path=profile_path, task=task, item=item
        )
        if not _same_decimal(instance.bid, before.get("bid")):
            raise ValidationError("建议 beforeValue 已漂移")
        _positive_decimal(after.get("bid"), "竞价")
    elif action_type == "ADD_KEYWORD":
        if item.get("objectType") != "AD_GROUP":
            raise ValidationError("动作与对象类型不匹配")
        _object_for_profile(
            model=AdGroup,
            profile_path="campaign__profile",
            task=task,
            item=item,
        )
        text = str(after.get("text") or "").strip()
        if not text or len(text) > 255 or after.get("matchType") not in MatchType.values:
            raise ValidationError("新增关键词参数无效")
        _positive_decimal(after.get("bid"), "竞价")
    elif action_type == "ADD_NEGATIVE_KEYWORD":
        object_type = item.get("objectType")
        if object_type == "CAMPAIGN":
            model, profile_path = Campaign, "profile"
        elif object_type == "AD_GROUP":
            model, profile_path = AdGroup, "campaign__profile"
        else:
            raise ValidationError("动作与对象类型不匹配")
        _object_for_profile(
            model=model, profile_path=profile_path, task=task, item=item
        )
        text = str(after.get("text") or "").strip()
        if not text or len(text) > 255 or after.get("matchType") not in MatchType.values:
            raise ValidationError("否定关键词参数无效")
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
