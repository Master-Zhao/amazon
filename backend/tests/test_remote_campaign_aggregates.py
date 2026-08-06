from datetime import date
from decimal import Decimal

from integrations.advertising_data.remote_campaign_aggregates import (
    RemoteCampaignAggregateReader,
    RemoteCampaignFieldMappings,
    _Watermarks,
)


def fact_row(**overrides):
    value = {
        "campaign_name": "事实表活动",
        "targeting_type": "SP-Auto",
        "state": "paused",
        "bidding_strategy": "legacy_for_sales",
        "start_date": date(2026, 7, 1),
        "daily_budget": Decimal("20"),
        "impressions": 1000,
        "clicks": 50,
        "spend": Decimal("75"),
        "orders": 10,
        "sales": Decimal("300"),
        "top_of_search_share": Decimal("0.30"),
    }
    value.update(overrides)
    return value


def scm_row(**overrides):
    value = {
        "reference_code": "SP-CODE-1",
        "campaign_name": "SCM 当前名称",
        "targeting_type": "SP-Auto",
        "state": "enabled",
        "start_date": date(2026, 6, 1),
        "end_date": None,
        "daily_budget": Decimal("100"),
        "bidding_strategy": "fixed_bids",
    }
    value.update(overrides)
    return value


def test_composite_fact_cte_deduplicates_each_table_then_prefers_realtime():
    sql = RemoteCampaignAggregateReader._fact_cte(
        RemoteCampaignFieldMappings(
            historical_impressions="imperssion",
            realtime_impressions="impression",
            historical_clicks="click",
            realtime_clicks="click",
        )
    )

    assert "FROM bi_analyze_ad_campaign\n" in sql
    assert "FROM bi_analyze_ad_campaign_realtime\n" in sql
    assert "PARTITION BY business_date, campaign_key, product_key, asin_key" in sql
    assert "ORDER BY source_priority DESC" in sql
    assert "SELECT * FROM source_ranked WHERE source_row_number = 1" in sql
    assert "type =" not in sql


def test_default_watermark_prefers_latest_date_with_real_metrics():
    watermarks = _Watermarks(
        history_through_date=date(2025, 12, 28),
        realtime_through_date=date(2026, 7, 17),
        metric_through_date=date(2025, 12, 28),
        realtime_as_of=None,
    )

    assert watermarks.latest_date == date(2025, 12, 28)


def test_merge_uses_campaign_code_universe_and_scm_current_metadata():
    items = RemoteCampaignAggregateReader._merge_campaigns(
        fact_rows={"SP-CODE-1": fact_row()},
        scm_rows={"SP-CODE-1": scm_row(), "SP-CODE-ONLY": scm_row(reference_code="SP-CODE-ONLY")},
    )

    matched, scm_only = items
    assert matched.campaign_key == "SP-CODE-1"
    assert matched.campaign_name == "SCM 当前名称"
    assert matched.state == "enabled"
    assert matched.impressions == 1000
    assert matched.top_of_search_share == Decimal("0.30")
    assert matched.scm_matched is True
    assert matched.has_metrics is True
    assert scm_only.campaign_key == "SP-CODE-ONLY"
    assert scm_only.has_metrics is False
    assert scm_only.impressions is None


def test_metric_filter_runs_on_aggregated_values_and_excludes_scm_only_rows():
    reader = RemoteCampaignAggregateReader.__new__(RemoteCampaignAggregateReader)
    items = RemoteCampaignAggregateReader._merge_campaigns(
        fact_rows={"SP-CODE-1": fact_row()},
        scm_rows={"SP-CODE-1": scm_row(), "SP-CODE-ONLY": scm_row(reference_code="SP-CODE-ONLY")},
    )

    filtered = reader._filter_campaigns(
        items,
        enabled=True,
        statuses=("enabled",),
        targeting_type="AUTO",
        search="SCM",
        metric_filters=(
            {"field": "impressions", "operator": "gte", "value": Decimal("1000")},
            {"field": "acos", "operator": "between", "value": Decimal("0.2"), "value2": Decimal("0.3")},
        ),
        exact_campaign_key=None,
    )

    assert [item.campaign_key for item in filtered] == ["SP-CODE-1"]
