import hashlib

from django.db import transaction

from apps.advertising.models import (
    AdGroup,
    AdProductType,
    Campaign,
    EntityState,
    Keyword,
    ProductTarget,
    SearchTerm,
)


def _upsert_campaigns(*, batch, rows: list[dict[str, object]]) -> dict[str, Campaign]:
    profile = batch.task.upload.profile
    latest = {str(row["campaign_id"]): row for row in rows}
    existing = {
        item.external_campaign_id: item
        for item in Campaign.objects.filter(
            profile=profile,
            external_campaign_id__in=latest,
        )
    }
    missing = [
        Campaign(
            profile=profile,
            external_campaign_id=external_id,
            name=str(row["campaign_name"]),
            ad_product_type=AdProductType.SPONSORED_PRODUCTS,
            state=str(row.get("campaign_status") or EntityState.UNKNOWN),
            daily_budget=row.get("daily_budget"),
            currency_code=str(row["currency"]),
            source_batch=batch,
        )
        for external_id, row in latest.items()
        if external_id not in existing
    ]
    if missing:
        Campaign.objects.bulk_create(missing)
    campaigns = {
        item.external_campaign_id: item
        for item in Campaign.objects.filter(
            profile=profile,
            external_campaign_id__in=latest,
        )
    }
    changed: list[Campaign] = []
    for external_id, row in latest.items():
        campaign = campaigns[external_id]
        campaign.name = str(row["campaign_name"])
        campaign.currency_code = str(row["currency"])
        campaign.source_batch = batch
        if "campaign_status" in row:
            campaign.state = str(row["campaign_status"])
        if "daily_budget" in row:
            campaign.daily_budget = row["daily_budget"]
        changed.append(campaign)
    Campaign.objects.bulk_update(
        changed,
        [
            "name",
            "currency_code",
            "source_batch",
            "state",
            "daily_budget",
            "updated_at",
        ],
    )
    return campaigns


def _upsert_ad_groups(
    *,
    batch,
    rows: list[dict[str, object]],
    campaigns: dict[str, Campaign],
) -> dict[tuple[int, str], AdGroup]:
    latest = {
        (campaigns[str(row["campaign_id"])].pk, str(row["ad_group_id"])): row
        for row in rows
    }
    existing = {
        (item.campaign_id, item.external_ad_group_id): item
        for item in AdGroup.objects.filter(
            campaign__profile=batch.task.upload.profile,
            external_ad_group_id__in={
                str(row["ad_group_id"]) for row in rows
            },
        )
    }
    missing = [
        AdGroup(
            campaign_id=campaign_id,
            external_ad_group_id=external_id,
            name=str(row["ad_group_name"]),
            state=EntityState.UNKNOWN,
            source_batch=batch,
        )
        for (campaign_id, external_id), row in latest.items()
        if (campaign_id, external_id) not in existing
    ]
    if missing:
        AdGroup.objects.bulk_create(missing)
    ad_groups = {
        (item.campaign_id, item.external_ad_group_id): item
        for item in AdGroup.objects.filter(
            campaign__profile=batch.task.upload.profile,
            external_ad_group_id__in={
                str(row["ad_group_id"]) for row in rows
            },
        )
    }
    changed: list[AdGroup] = []
    for key, row in latest.items():
        ad_group = ad_groups[key]
        ad_group.name = str(row["ad_group_name"])
        ad_group.source_batch = batch
        changed.append(ad_group)
    AdGroup.objects.bulk_update(changed, ["name", "source_batch", "updated_at"])
    return ad_groups


@transaction.atomic
def upsert_campaign_report_entities(
    *,
    batch,
    rows: list[dict[str, object]],
) -> dict[str, Campaign]:
    return _upsert_campaigns(batch=batch, rows=rows)


@transaction.atomic
def upsert_targeting_report_entities(
    *,
    batch,
    rows: list[dict[str, object]],
) -> None:
    campaigns = _upsert_campaigns(batch=batch, rows=rows)
    ad_groups = _upsert_ad_groups(
        batch=batch,
        rows=rows,
        campaigns=campaigns,
    )

    keyword_rows = [row for row in rows if row["target_type"] == "KEYWORD"]
    keyword_ids = {str(row["target_id"]) for row in keyword_rows}
    existing_keywords = {
        (item.ad_group_id, item.external_keyword_id): item
        for item in Keyword.objects.filter(
            ad_group__campaign__profile=batch.task.upload.profile,
            external_keyword_id__in=keyword_ids,
        )
    }
    new_keywords: list[Keyword] = []
    changed_keywords: list[Keyword] = []
    for row in keyword_rows:
        ad_group = ad_groups[
            (
                campaigns[str(row["campaign_id"])].pk,
                str(row["ad_group_id"]),
            )
        ]
        key = (ad_group.pk, str(row["target_id"]))
        keyword = existing_keywords.get(key)
        if keyword is None:
            new_keywords.append(
                Keyword(
                    ad_group=ad_group,
                    external_keyword_id=str(row["target_id"]),
                    keyword_text=str(row["target_text"]),
                    match_type=str(row["match_type"]),
                    state=str(row["target_status"]),
                    bid=row["bid"],
                    source_batch=batch,
                )
            )
        else:
            keyword.keyword_text = str(row["target_text"])
            keyword.match_type = str(row["match_type"])
            keyword.state = str(row["target_status"])
            keyword.bid = row["bid"]
            keyword.source_batch = batch
            changed_keywords.append(keyword)
    if new_keywords:
        Keyword.objects.bulk_create(new_keywords)
    if changed_keywords:
        Keyword.objects.bulk_update(
            changed_keywords,
            ["keyword_text", "match_type", "state", "bid", "source_batch"],
        )

    target_rows = [
        row for row in rows if row["target_type"] == "PRODUCT_TARGET"
    ]
    target_ids = {str(row["target_id"]) for row in target_rows}
    existing_targets = {
        (item.ad_group_id, item.external_target_id): item
        for item in ProductTarget.objects.filter(
            ad_group__campaign__profile=batch.task.upload.profile,
            external_target_id__in=target_ids,
        )
    }
    new_targets: list[ProductTarget] = []
    changed_targets: list[ProductTarget] = []
    for row in target_rows:
        ad_group = ad_groups[
            (
                campaigns[str(row["campaign_id"])].pk,
                str(row["ad_group_id"]),
            )
        ]
        key = (ad_group.pk, str(row["target_id"]))
        target = existing_targets.get(key)
        if target is None:
            new_targets.append(
                ProductTarget(
                    ad_group=ad_group,
                    external_target_id=str(row["target_id"]),
                    expression=str(row["target_text"]),
                    state=str(row["target_status"]),
                    bid=row["bid"],
                    source_batch=batch,
                )
            )
        else:
            target.expression = str(row["target_text"])
            target.state = str(row["target_status"])
            target.bid = row["bid"]
            target.source_batch = batch
            changed_targets.append(target)
    if new_targets:
        ProductTarget.objects.bulk_create(new_targets)
    if changed_targets:
        ProductTarget.objects.bulk_update(
            changed_targets,
            ["expression", "state", "bid", "source_batch"],
        )


@transaction.atomic
def upsert_search_term_report_entities(
    *,
    batch,
    rows: list[dict[str, object]],
) -> None:
    campaigns = _upsert_campaigns(batch=batch, rows=rows)
    _upsert_ad_groups(batch=batch, rows=rows, campaigns=campaigns)
    prepared: dict[str, tuple[str, str]] = {}
    for row in rows:
        display = " ".join(str(row["search_term"]).split())
        normalized = display.casefold()
        text_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        row["search_term_hash"] = text_hash
        prepared[text_hash] = (normalized, display)
    existing = set(
        SearchTerm.objects.filter(
            profile=batch.task.upload.profile,
            text_hash__in=prepared,
        ).values_list("text_hash", flat=True)
    )
    SearchTerm.objects.bulk_create(
        [
            SearchTerm(
                profile=batch.task.upload.profile,
                normalized_text=normalized,
                text_hash=text_hash,
                display_text=display,
            )
            for text_hash, (normalized, display) in prepared.items()
            if text_hash not in existing
        ]
    )
