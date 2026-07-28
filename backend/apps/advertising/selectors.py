from rest_framework.exceptions import NotFound

from apps.advertising.models import Campaign, Keyword, ProductTarget, SearchTerm
from apps.permissions.services import authorize
from apps.stores.models import AdvertisingProfile


def _profile(user, tenant_id, profile_id):
    try:
        profile = AdvertisingProfile.objects.select_related(
            "store_marketplace__store"
        ).get(pk=profile_id)
    except (AdvertisingProfile.DoesNotExist, ValueError) as exc:
        raise NotFound("广告 Profile 不存在") from exc
    authorize(
        user=user,
        tenant_id=tenant_id,
        permission_code="reports.view",
        profile=profile,
    )
    return profile


def campaigns(user, tenant_id, profile_id, *, offset=0, limit=50):
    profile = _profile(user, tenant_id, profile_id)
    query = Campaign.objects.filter(profile=profile).order_by("name", "pk")
    return [
        {
            "id": str(item.pk),
            "external_campaign_id": item.external_campaign_id,
            "name": item.name,
            "state": item.state,
            "daily_budget": str(item.daily_budget) if item.daily_budget is not None else None,
            "currency": item.currency,
        }
        for item in query[offset : offset + limit]
    ], query.count()


def targeting(user, tenant_id, profile_id, *, offset=0, limit=50):
    profile = _profile(user, tenant_id, profile_id)
    keyword_query = Keyword.objects.filter(
        ad_group__campaign__profile=profile
    ).select_related("ad_group").order_by("pk")
    target_query = ProductTarget.objects.filter(
        ad_group__campaign__profile=profile
    ).select_related("ad_group").order_by("pk")
    keyword_count = keyword_query.count()
    target_count = target_query.count()
    keywords = []
    targets = []
    if offset < keyword_count:
        keywords = list(keyword_query[offset : min(keyword_count, offset + limit)])
    remaining = limit - len(keywords)
    if remaining:
        target_offset = max(0, offset - keyword_count)
        targets = list(target_query[target_offset : target_offset + remaining])
    return [
        {
            "id": str(item.pk),
            "type": "KEYWORD",
            "text": item.text,
            "state": item.state,
            "bid": str(item.bid) if item.bid is not None else None,
        }
        for item in keywords
    ] + [
        {
            "id": str(item.pk),
            "type": "PRODUCT",
            "text": item.expression,
            "state": item.state,
            "bid": str(item.bid) if item.bid is not None else None,
        }
        for item in targets
    ], keyword_count + target_count


def search_terms(user, tenant_id, profile_id, *, offset=0, limit=50):
    profile = _profile(user, tenant_id, profile_id)
    query = SearchTerm.objects.filter(profile=profile).order_by("query_text", "pk")
    return [
        {
            "id": str(item.pk),
            "search_term": item.query_text,
            "targeting_text": item.targeting_text,
        }
        for item in query[offset : offset + limit]
    ], query.count()
