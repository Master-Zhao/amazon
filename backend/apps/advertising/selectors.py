from apps.advertising.models import Campaign, Keyword, ProductTarget, SearchTerm
from apps.permissions.models import ProfileAccessLevel
from apps.permissions.services import require_profile_scope


def campaign_rows(*, user, tenant_id, profile_id) -> list[dict[str, object]]:
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="advertising.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    return [
        {
            "id": str(item.pk),
            "external_campaign_id": item.external_campaign_id,
            "name": item.name,
            "ad_product_type": item.ad_product_type,
            "state": item.state,
            "daily_budget": (
                str(item.daily_budget) if item.daily_budget is not None else None
            ),
            "currency_code": item.currency_code,
            "source_batch_id": (
                str(item.source_batch_id) if item.source_batch_id else None
            ),
        }
        for item in Campaign.objects.filter(profile=scope.profile).order_by(
            "name",
            "external_campaign_id",
        )
    ]


def targeting_rows(*, user, tenant_id, profile_id) -> list[dict[str, object]]:
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="advertising.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    keywords = [
        {
            "id": str(item.pk),
            "target_type": "KEYWORD",
            "external_target_id": item.external_keyword_id,
            "target_text": item.keyword_text,
            "match_type": item.match_type,
            "state": item.state,
            "bid": str(item.bid) if item.bid is not None else None,
            "campaign_id": str(item.ad_group.campaign_id),
            "campaign_name": item.ad_group.campaign.name,
            "ad_group_id": str(item.ad_group_id),
            "ad_group_name": item.ad_group.name,
            "source_batch_id": (
                str(item.source_batch_id) if item.source_batch_id else None
            ),
        }
        for item in Keyword.objects.select_related(
            "ad_group__campaign"
        ).filter(
            ad_group__campaign__profile=scope.profile,
        )
    ]
    targets = [
        {
            "id": str(item.pk),
            "target_type": "PRODUCT_TARGET",
            "external_target_id": item.external_target_id,
            "target_text": item.expression,
            "match_type": None,
            "state": item.state,
            "bid": str(item.bid) if item.bid is not None else None,
            "campaign_id": str(item.ad_group.campaign_id),
            "campaign_name": item.ad_group.campaign.name,
            "ad_group_id": str(item.ad_group_id),
            "ad_group_name": item.ad_group.name,
            "source_batch_id": (
                str(item.source_batch_id) if item.source_batch_id else None
            ),
        }
        for item in ProductTarget.objects.select_related(
            "ad_group__campaign"
        ).filter(
            ad_group__campaign__profile=scope.profile,
        )
    ]
    return sorted(
        [*keywords, *targets],
        key=lambda item: (
            item["campaign_name"],
            item["ad_group_name"],
            item["target_type"],
            item["target_text"],
        ),
    )


def search_term_rows(*, user, tenant_id, profile_id) -> list[dict[str, object]]:
    scope = require_profile_scope(
        user=user,
        tenant_id=tenant_id,
        profile_id=profile_id,
        permission_code="advertising.view",
        minimum_level=ProfileAccessLevel.VIEW,
    )
    return [
        {
            "id": str(item.pk),
            "display_text": item.display_text,
            "normalized_text": item.normalized_text,
            "text_hash": item.text_hash,
        }
        for item in SearchTerm.objects.filter(profile=scope.profile).order_by(
            "normalized_text"
        )
    ]
