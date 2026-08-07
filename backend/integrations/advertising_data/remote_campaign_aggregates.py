from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from typing import Iterable
from uuid import uuid4

from django.conf import settings
from django.db import DatabaseError, connections

from apps.analytics.calculations import calculate_metrics

from .remote_databases import (
    ANALYSIS_ALIAS,
    SCM_ALIAS,
    RemoteAdvertisingDataUnavailable,
    RemoteCampaignDailyTotals,
    RemoteCampaignMetric,
    RemoteCampaignOverviewMetric,
    RemoteCampaignOverviewPage,
    RemoteCampaignOverviewTotals,
    RemoteCampaignRiskMetric,
)

logger = logging.getLogger(__name__)

HISTORY_TABLE = "bi_analyze_ad_campaign"
REALTIME_TABLE = "bi_analyze_ad_campaign_realtime"
SCM_TABLE = "eb_ad_campaign"
DEDUPLICATION_VERSION = "campaign-code-product-asin-realtime-v1"

METRIC_FILTER_FIELDS = frozenset(
    {"impressions", "clicks", "spend", "orders", "cpc", "acos", "ctr", "cvr"}
)
METRIC_FILTER_OPERATORS = frozenset({"gte", "lte", "eq", "between"})


@dataclass(frozen=True, slots=True)
class RemoteCampaignFieldMappings:
    historical_impressions: str
    realtime_impressions: str
    historical_clicks: str
    realtime_clicks: str
    campaign_join_key: str = "campaign_code->code"

    def as_dict(self) -> dict[str, str]:
        return {
            "historicalImpressions": self.historical_impressions,
            "realtimeImpressions": self.realtime_impressions,
            "historicalClicks": self.historical_clicks,
            "realtimeClicks": self.realtime_clicks,
            "campaignJoinKey": self.campaign_join_key,
        }


@dataclass(frozen=True, slots=True)
class _Watermarks:
    history_through_date: date | None
    realtime_through_date: date | None
    metric_through_date: date | None
    realtime_as_of: datetime | None

    @property
    def latest_date(self) -> date | None:
        if self.metric_through_date is not None:
            return self.metric_through_date
        values = [
            value
            for value in (self.history_through_date, self.realtime_through_date)
            if value is not None
        ]
        return max(values) if values else None


def _decimal(value: object) -> Decimal:
    return Decimal(str(value or 0))


def _as_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    return value if isinstance(value, date) else None


def _normal_targeting_type(value: object) -> str:
    normalized = str(value or "").strip().lower().replace("_", "-")
    if "auto" in normalized:
        return "auto"
    if "manual" in normalized:
        return "manual"
    return normalized or "unknown"


@lru_cache(maxsize=8)
def _remote_columns(alias: str, table: str) -> frozenset[str]:
    if alias not in settings.DATABASES:
        raise RemoteAdvertisingDataUnavailable(
            f"远程数据库别名 {alias} 未配置"
        )
    with connections[alias].cursor() as cursor:
        cursor.execute(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
            """,
            [table],
        )
        return frozenset(str(row[0]) for row in cursor.fetchall())


def clear_remote_schema_cache() -> None:
    _remote_columns.cache_clear()


class RemoteCampaignAggregateReader:
    def __init__(self, *, scm_connection=None, analysis_connection=None):
        self.scm_connection = scm_connection or connections[SCM_ALIAS]
        self.analysis_connection = analysis_connection or connections[ANALYSIS_ALIAS]

    def campaign_overview(
        self,
        *,
        merchant_id: int,
        merchant_code: str,
        start_date: date | None,
        end_date: date | None,
        enabled: bool | None,
        statuses: tuple[str, ...],
        targeting_type: str | None,
        search: str,
        metric_filters: tuple[dict[str, object], ...],
        ordering: str,
        page: int,
        page_size: int,
        include_summary: bool,
        require_metrics: bool = False,
        exact_campaign_key: str | None = None,
    ) -> RemoteCampaignOverviewPage:
        try:
            mappings = self._field_mappings()
            watermarks = self._watermarks(
                merchant_id=merchant_id,
                merchant_code=merchant_code,
                mappings=mappings,
            )
            effective_start, effective_end = self._overview_dates(
                start_date=start_date,
                end_date=end_date,
                latest=watermarks.latest_date,
            )
            fact_rows = (
                self._fact_campaign_rows(
                    merchant_id=merchant_id,
                    merchant_code=merchant_code,
                    start_date=effective_start,
                    end_date=effective_end,
                    mappings=mappings,
                )
                if effective_start is not None and effective_end is not None
                else {}
            )
            scm_rows = self._scm_rows(
                merchant_id=merchant_id,
                merchant_code=merchant_code,
            )
            merged = self._merge_campaigns(fact_rows=fact_rows, scm_rows=scm_rows)
            if require_metrics:
                merged = [item for item in merged if item.has_metrics]
            filtered = self._filter_campaigns(
                merged,
                enabled=enabled,
                statuses=statuses,
                targeting_type=targeting_type,
                search=search,
                metric_filters=metric_filters,
                exact_campaign_key=exact_campaign_key,
            )
            ordered = self._order_campaigns(filtered, ordering=ordering)
            total = len(ordered)
            offset = (page - 1) * page_size
            items = ordered[offset : offset + page_size]
            summary = self._summary(filtered) if include_summary else None
            fact_keys = [item.campaign_key for item in filtered if item.has_metrics]
            trend = (
                self._daily_totals(
                    merchant_id=merchant_id,
                    merchant_code=merchant_code,
                    start_date=effective_start,
                    end_date=effective_end,
                    campaign_keys=fact_keys,
                    mappings=mappings,
                )
                if effective_start is not None
                and effective_end is not None
                and fact_keys
                else []
            )
            risk_metrics = [
                RemoteCampaignRiskMetric(
                    campaign_key=item.campaign_key,
                    impressions=int(item.impressions or 0),
                    clicks=int(item.clicks or 0),
                    spend=_decimal(item.spend),
                    orders=int(item.orders or 0),
                    sales=_decimal(item.sales),
                )
                for item in filtered[:10_000]
                if item.has_metrics
            ]
            if sum(1 for item in filtered if item.has_metrics) > 10_000:
                raise RemoteAdvertisingDataUnavailable(
                    "当前筛选范围超过风险统计上限，请缩小日期或筛选范围"
                )
        except DatabaseError as exc:
            raise RemoteAdvertisingDataUnavailable() from exc

        return RemoteCampaignOverviewPage(
            items=items,
            summary=summary,
            page=page,
            page_size=page_size,
            total=total,
            start_date=effective_start,
            end_date=effective_end,
            data_through_date=watermarks.latest_date,
            history_through_date=watermarks.history_through_date,
            realtime_through_date=watermarks.realtime_through_date,
            realtime_as_of=watermarks.realtime_as_of,
            deduplication_version=DEDUPLICATION_VERSION,
            field_mappings=mappings.as_dict(),
            trend=trend,
            risk_metrics=risk_metrics,
        )

    def campaign_metrics(
        self,
        *,
        merchant_id: int,
        merchant_code: str,
        start_date: date | None,
        end_date: date | None,
    ) -> list[RemoteCampaignMetric]:
        mappings = self._field_mappings()
        watermarks = self._watermarks(
            merchant_id=merchant_id,
            merchant_code=merchant_code,
            mappings=mappings,
        )
        if watermarks.latest_date is None:
            return []
        effective_start, effective_end = self._overview_dates(
            start_date=start_date,
            end_date=end_date,
            latest=watermarks.latest_date,
        )
        if effective_start is None or effective_end is None:
            return []
        fact_rows = self._fact_campaign_rows(
            merchant_id=merchant_id,
            merchant_code=merchant_code,
            start_date=effective_start,
            end_date=effective_end,
            mappings=mappings,
        )
        scm_rows = self._scm_rows(
            merchant_id=merchant_id,
            merchant_code=merchant_code,
        )
        merged = self._merge_campaigns(fact_rows=fact_rows, scm_rows=scm_rows)
        eligible = [item for item in merged if item.has_metrics]
        if len(eligible) > settings.REMOTE_AD_MAX_ROWS:
            logger.warning(
                "Remote campaign metrics truncated: %d campaigns exceed limit %d",
                len(eligible),
                settings.REMOTE_AD_MAX_ROWS,
            )
        return [
            RemoteCampaignMetric(
                report_date=effective_end,
                external_campaign_id=item.campaign_key,
                campaign_name=item.campaign_name,
                impressions=int(item.impressions or 0),
                clicks=int(item.clicks or 0),
                spend=_decimal(item.spend),
                orders=int(item.orders or 0),
                sales=_decimal(item.sales),
                daily_budget=item.daily_budget,
                state=item.state,
                scm_matched=item.scm_matched,
            )
            for item in eligible[: settings.REMOTE_AD_MAX_ROWS]
        ]

    def update_campaign_enabled(
        self,
        *,
        merchant_id: int,
        merchant_code: str,
        campaign_key: str,
        enabled: bool,
        campaign_name: str | None = None,
        targeting_type: str | None = None,
        daily_budget: Decimal | None = None,
        bidding_strategy: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        actor_id: int | None = None,
        actor_name: str = "",
    ) -> bool:
        target_state = "enabled" if enabled else "paused"
        if campaign_key.startswith("ID:"):
            selector = "(COALESCE(NULLIF(code, ''), CONCAT('ID:', campaign_id)) = %s)"
        else:
            selector = "code = %s"
        where = f"""
            mer_id = %s AND mer_code = %s
            AND COALESCE(status, 0) <> 6
            AND {selector}
        """
        params = [merchant_id, merchant_code, campaign_key]
        try:
            with self.scm_connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT COUNT(1) FROM {SCM_TABLE} WHERE {where}",
                    params,
                )
                if int(cursor.fetchone()[0] or 0) == 0:
                    cursor.execute(
                        f"""
                        INSERT INTO {SCM_TABLE} (
                            mer_id, mer_code, type, code, name, start_date, end_date,
                            state, budget, bidding_strategy, create_by, create_name,
                            create_time, update_by, update_name, update_time, status
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            NOW(), %s, %s, NOW(), 0
                        )
                        """,
                        [
                            merchant_id,
                            merchant_code,
                            _normal_targeting_type(targeting_type or "manual"),
                            campaign_key,
                            (campaign_name or campaign_key)[:255],
                            start_date or date.today(),
                            end_date,
                            target_state,
                            daily_budget,
                            bidding_strategy or "down_only",
                            actor_id or 0,
                            actor_name[:45] or "Codex",
                            actor_id or 0,
                            actor_name[:45] or "Codex",
                        ],
                    )
                    return True
                cursor.execute(
                    f"""
                    UPDATE {SCM_TABLE}
                    SET state = %s, update_time = NOW()
                    WHERE {where}
                    """,
                    [target_state, *params],
                )
        except DatabaseError as exc:
            raise RemoteAdvertisingDataUnavailable() from exc
        return True

    def create_campaign(
        self,
        *,
        merchant_id: int,
        merchant_code: str,
        name: str,
        targeting_type: str,
        daily_budget: Decimal,
        bidding_strategy: str,
        start_date: date,
        end_date: date | None,
        enabled: bool,
        actor_id: int | None,
        actor_name: str,
    ) -> str:
        campaign_code = f"CODX-{merchant_code}-{uuid4().hex[:20]}"
        state = "enabled" if enabled else "paused"
        remote_type = _normal_targeting_type(targeting_type)
        if remote_type not in {"auto", "manual"}:
            remote_type = "manual"
        try:
            with self.scm_connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {SCM_TABLE} (
                        mer_id, mer_code, type, code, name, start_date, end_date,
                        state, budget, bidding_strategy, create_by, create_name,
                        create_time, update_by, update_name, update_time, status
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        NOW(), %s, %s, NOW(), 0
                    )
                    """,
                    [
                        merchant_id,
                        merchant_code,
                        remote_type,
                        campaign_code,
                        name,
                        start_date,
                        end_date,
                        state,
                        daily_budget,
                        bidding_strategy,
                        actor_id or 0,
                        actor_name[:45] or "Codex",
                        actor_id or 0,
                        actor_name[:45] or "Codex",
                    ],
                )
        except DatabaseError as exc:
            raise RemoteAdvertisingDataUnavailable() from exc
        return campaign_code

    def _field_mappings(self) -> RemoteCampaignFieldMappings:
        history = _remote_columns(ANALYSIS_ALIAS, HISTORY_TABLE)
        realtime = _remote_columns(ANALYSIS_ALIAS, REALTIME_TABLE)
        scm = _remote_columns(SCM_ALIAS, SCM_TABLE)
        required_history = {
            "id",
            "mer_id",
            "mer_code",
            "creation_date",
            "campaign_code",
            "campaign_id",
            "campaign_name",
            "campaign_type",
            "campaign_state",
            "campaign_bidding_strategy",
            "campaign_daily_budget",
            "campaign_create_date",
            "product_id",
            "asin",
            "spend",
            "orders",
            "sales",
            "create_time",
        }
        required_realtime = required_history | {
            "update_time",
            "type",
            "campaign_targeting_type",
            "serving_status",
            "daily_budget",
            "bidding_strategy",
        }
        required_scm = {
            "id",
            "mer_id",
            "mer_code",
            "campaign_id",
            "code",
            "name",
            "type",
            "state",
            "start_date",
            "end_date",
            "budget",
            "bidding_strategy",
            "update_time",
            "status",
        }
        missing = {
            HISTORY_TABLE: sorted(required_history - history),
            REALTIME_TABLE: sorted(required_realtime - realtime),
            SCM_TABLE: sorted(required_scm - scm),
        }
        missing = {table: values for table, values in missing.items() if values}
        if missing:
            raise RemoteAdvertisingDataUnavailable(
                f"远程 Campaign Schema 缺少必要字段：{missing}"
            )

        def resolve(columns: frozenset[str], candidates: Iterable[str]) -> str:
            for candidate in candidates:
                if candidate in columns:
                    return candidate
            raise RemoteAdvertisingDataUnavailable("远程 Campaign 指标字段映射失败")

        return RemoteCampaignFieldMappings(
            historical_impressions=resolve(history, ("imperssion", "impression")),
            realtime_impressions=resolve(realtime, ("impression", "imperssion")),
            historical_clicks=resolve(history, ("click", "clicks")),
            realtime_clicks=resolve(realtime, ("click", "clicks")),
        )

    def _watermarks(
        self,
        *,
        merchant_id: int,
        merchant_code: str,
        mappings: RemoteCampaignFieldMappings,
    ) -> _Watermarks:
        with self.analysis_connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT MAX(DATE(creation_date))
                FROM {HISTORY_TABLE}
                WHERE mer_id = %s AND mer_code = %s
                """,
                [merchant_id, merchant_code],
            )
            history_through_date = cursor.fetchone()[0]
            cursor.execute(
                f"""
                SELECT MAX(DATE(creation_date))
                FROM {HISTORY_TABLE}
                WHERE mer_id = %s AND mer_code = %s
                  AND (
                    COALESCE(spend, 0) <> 0
                    OR COALESCE(orders, 0) <> 0
                    OR COALESCE(sales, 0) <> 0
                  )
                """,
                [merchant_id, merchant_code],
            )
            history_metric_through_date = cursor.fetchone()[0]
            cursor.execute(
                f"""
                SELECT MAX(DATE(creation_date)),
                       MAX(COALESCE(update_time, create_time, creation_date))
                FROM {REALTIME_TABLE}
                WHERE mer_id = %s AND mer_code = %s
                """,
                [merchant_id, merchant_code],
            )
            realtime_through_date, realtime_as_of = cursor.fetchone()
            cursor.execute(
                f"""
                SELECT MAX(DATE(creation_date))
                FROM {REALTIME_TABLE}
                WHERE mer_id = %s AND mer_code = %s
                  AND (
                    COALESCE(spend, 0) <> 0
                    OR COALESCE(orders, 0) <> 0
                    OR COALESCE(sales, 0) <> 0
                  )
                """,
                [merchant_id, merchant_code],
            )
            realtime_metric_through_date = cursor.fetchone()[0]
        metric_dates = [
            value
            for value in (history_metric_through_date, realtime_metric_through_date)
            if value is not None
        ]
        return _Watermarks(
            history_through_date=history_through_date,
            realtime_through_date=realtime_through_date,
            metric_through_date=max(metric_dates) if metric_dates else None,
            realtime_as_of=realtime_as_of,
        )

    @staticmethod
    def _overview_dates(
        *, start_date: date | None, end_date: date | None, latest: date | None
    ) -> tuple[date | None, date | None]:
        if start_date is not None and end_date is not None:
            return start_date, end_date
        if latest is None:
            return None, None
        effective_end = end_date or latest
        return start_date or (effective_end - timedelta(days=29)), effective_end

    @staticmethod
    def _fact_cte(mappings: RemoteCampaignFieldMappings) -> str:
        return f"""
            WITH historical_ranked AS (
                SELECT
                    id AS source_record_id,
                    DATE(creation_date) AS business_date,
                    COALESCE(NULLIF(campaign_code, ''), CONCAT('ID:', campaign_id)) AS campaign_key,
                    COALESCE(product_id, 0) AS product_key,
                    COALESCE(asin, '') AS asin_key,
                    campaign_name,
                    campaign_type AS targeting_type,
                    campaign_state,
                    campaign_bidding_strategy AS bidding_strategy,
                    campaign_create_date,
                    campaign_daily_budget AS daily_budget,
                    COALESCE({mappings.historical_impressions}, 0) AS impressions,
                    COALESCE({mappings.historical_clicks}, 0) AS clicks,
                    COALESCE(spend, 0) AS spend,
                    COALESCE(orders, 0) AS orders,
                    COALESCE(sales, 0) AS sales,
                    top_of_search_is AS top_of_search_share,
                    COALESCE(create_time, creation_date) AS observed_at,
                    1 AS source_priority,
                    ROW_NUMBER() OVER (
                        PARTITION BY DATE(creation_date),
                                     COALESCE(NULLIF(campaign_code, ''), CONCAT('ID:', campaign_id)),
                                     COALESCE(product_id, 0), COALESCE(asin, '')
                        ORDER BY COALESCE(create_time, creation_date) DESC, id DESC
                    ) AS table_row_number
                FROM {HISTORY_TABLE}
                WHERE mer_id = %s AND mer_code = %s
                  AND creation_date >= %s AND creation_date < %s
                  AND COALESCE(NULLIF(campaign_code, ''), CONCAT('ID:', campaign_id)) IS NOT NULL
            ), realtime_ranked AS (
                SELECT
                    id AS source_record_id,
                    DATE(creation_date) AS business_date,
                    COALESCE(NULLIF(campaign_code, ''), CONCAT('ID:', campaign_id)) AS campaign_key,
                    COALESCE(product_id, 0) AS product_key,
                    COALESCE(asin, '') AS asin_key,
                    campaign_name,
                    COALESCE(campaign_targeting_type, campaign_type, type) AS targeting_type,
                    COALESCE(serving_status, campaign_state) AS campaign_state,
                    COALESCE(bidding_strategy, campaign_bidding_strategy) AS bidding_strategy,
                    campaign_create_date,
                    COALESCE(daily_budget, campaign_daily_budget) AS daily_budget,
                    COALESCE({mappings.realtime_impressions}, 0) AS impressions,
                    COALESCE({mappings.realtime_clicks}, 0) AS clicks,
                    COALESCE(spend, 0) AS spend,
                    COALESCE(orders, 0) AS orders,
                    COALESCE(sales, 0) AS sales,
                    NULL AS top_of_search_share,
                    COALESCE(update_time, create_time, creation_date) AS observed_at,
                    2 AS source_priority,
                    ROW_NUMBER() OVER (
                        PARTITION BY DATE(creation_date),
                                     COALESCE(NULLIF(campaign_code, ''), CONCAT('ID:', campaign_id)),
                                     COALESCE(product_id, 0), COALESCE(asin, '')
                        ORDER BY COALESCE(update_time, create_time, creation_date) DESC, id DESC
                    ) AS table_row_number
                FROM {REALTIME_TABLE}
                WHERE mer_id = %s AND mer_code = %s
                  AND creation_date >= %s AND creation_date < %s
                  AND COALESCE(NULLIF(campaign_code, ''), CONCAT('ID:', campaign_id)) IS NOT NULL
            ), normalized_facts AS (
                SELECT * FROM historical_ranked WHERE table_row_number = 1
                UNION ALL
                SELECT * FROM realtime_ranked WHERE table_row_number = 1
            ), source_ranked AS (
                SELECT normalized_facts.*,
                       ROW_NUMBER() OVER (
                           PARTITION BY business_date, campaign_key, product_key, asin_key
                           ORDER BY source_priority DESC, observed_at DESC, source_record_id DESC
                       ) AS source_row_number
                FROM normalized_facts
            ), selected_facts AS (
                SELECT * FROM source_ranked WHERE source_row_number = 1
            )
        """

    @staticmethod
    def _fact_parameters(
        *, merchant_id: int, merchant_code: str, start_date: date, end_date: date
    ) -> list[object]:
        end_exclusive = end_date + timedelta(days=1)
        return [
            merchant_id,
            merchant_code,
            start_date,
            end_exclusive,
            merchant_id,
            merchant_code,
            start_date,
            end_exclusive,
        ]

    def _fact_campaign_rows(
        self,
        *,
        merchant_id: int,
        merchant_code: str,
        start_date: date,
        end_date: date,
        mappings: RemoteCampaignFieldMappings,
    ) -> dict[str, dict[str, object]]:
        cte = self._fact_cte(mappings)
        with self.analysis_connection.cursor() as cursor:
            cursor.execute(
                f"""
                {cte}, campaign_totals AS (
                    SELECT campaign_key,
                           SUM(impressions) AS impressions,
                           SUM(clicks) AS clicks,
                           SUM(spend) AS spend,
                           SUM(orders) AS orders,
                           SUM(sales) AS sales,
                           CASE
                               WHEN SUM(CASE WHEN top_of_search_share IS NOT NULL THEN impressions ELSE 0 END) > 0
                               THEN SUM(top_of_search_share * impressions)
                                    / NULLIF(SUM(CASE WHEN top_of_search_share IS NOT NULL THEN impressions ELSE 0 END), 0)
                               ELSE AVG(top_of_search_share)
                           END AS top_of_search_share
                    FROM selected_facts
                    GROUP BY campaign_key
                ), historical_top_search AS (
                    SELECT campaign_key,
                           CASE
                               WHEN SUM(CASE WHEN top_of_search_share IS NOT NULL THEN impressions ELSE 0 END) > 0
                               THEN SUM(top_of_search_share * impressions)
                                    / NULLIF(SUM(CASE WHEN top_of_search_share IS NOT NULL THEN impressions ELSE 0 END), 0)
                               ELSE AVG(top_of_search_share)
                           END AS top_of_search_share
                    FROM historical_ranked
                    WHERE table_row_number = 1
                    GROUP BY campaign_key
                ), latest_metadata AS (
                    SELECT campaign_key, campaign_name, targeting_type,
                           campaign_state, bidding_strategy, campaign_create_date,
                           daily_budget,
                           ROW_NUMBER() OVER (
                               PARTITION BY campaign_key
                               ORDER BY business_date DESC, source_priority DESC,
                                        observed_at DESC, source_record_id DESC
                           ) AS campaign_row_number
                    FROM selected_facts
                )
                SELECT totals.campaign_key, metadata.campaign_name,
                       metadata.targeting_type, metadata.campaign_state,
                       metadata.bidding_strategy, metadata.campaign_create_date,
                       metadata.daily_budget, totals.impressions, totals.clicks,
                       totals.spend, totals.orders, totals.sales,
                       COALESCE(totals.top_of_search_share, top_search.top_of_search_share)
                FROM campaign_totals totals
                INNER JOIN latest_metadata metadata
                    ON metadata.campaign_key = totals.campaign_key
                   AND metadata.campaign_row_number = 1
                LEFT JOIN historical_top_search top_search
                    ON top_search.campaign_key = totals.campaign_key
                ORDER BY totals.campaign_key
                """,
                self._fact_parameters(
                    merchant_id=merchant_id,
                    merchant_code=merchant_code,
                    start_date=start_date,
                    end_date=end_date,
                ),
            )
            rows = cursor.fetchall()
        return {
            str(row[0]): {
                "campaign_name": row[1],
                "targeting_type": row[2],
                "state": row[3],
                "bidding_strategy": row[4],
                "start_date": row[5],
                "daily_budget": row[6],
                "impressions": int(row[7] or 0),
                "clicks": int(row[8] or 0),
                "spend": _decimal(row[9]),
                "orders": int(row[10] or 0),
                "sales": _decimal(row[11]),
                "top_of_search_share": row[12],
            }
            for row in rows
        }

    def _scm_rows(
        self, *, merchant_id: int, merchant_code: str
    ) -> dict[str, dict[str, object]]:
        with self.scm_connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT code, campaign_id, name, type, state, start_date, end_date,
                       budget, bidding_strategy
                FROM {SCM_TABLE}
                WHERE mer_id = %s AND mer_code = %s
                  AND COALESCE(status, 0) <> 6
                  AND COALESCE(NULLIF(code, ''), CONCAT('ID:', campaign_id)) IS NOT NULL
                ORDER BY update_time DESC, id DESC
                """,
                [merchant_id, merchant_code],
            )
            result: dict[str, dict[str, object]] = {}
            for row in cursor.fetchall():
                key = str(row[0] or f"ID:{row[1]}")
                result.setdefault(
                    key,
                    {
                        "reference_code": row[0] or key,
                        "campaign_name": row[2],
                        "targeting_type": row[3],
                        "state": row[4],
                        "start_date": row[5],
                        "end_date": row[6],
                        "daily_budget": row[7],
                        "bidding_strategy": row[8],
                    },
                )
        return result

    @staticmethod
    def _merge_campaigns(
        *,
        fact_rows: dict[str, dict[str, object]],
        scm_rows: dict[str, dict[str, object]],
    ) -> list[RemoteCampaignOverviewMetric]:
        items: list[RemoteCampaignOverviewMetric] = []
        for campaign_key in sorted(set(fact_rows) | set(scm_rows)):
            fact = fact_rows.get(campaign_key)
            scm = scm_rows.get(campaign_key)
            source = scm or fact or {}
            items.append(
                RemoteCampaignOverviewMetric(
                    campaign_key=campaign_key,
                    reference_code=str((scm or {}).get("reference_code") or campaign_key),
                    campaign_name=str(
                        (scm or {}).get("campaign_name")
                        or (fact or {}).get("campaign_name")
                        or campaign_key
                    ),
                    targeting_type=str(
                        (scm or {}).get("targeting_type")
                        or (fact or {}).get("targeting_type")
                        or "unknown"
                    ),
                    state=str(
                        (scm or {}).get("state")
                        or (fact or {}).get("state")
                        or "unknown"
                    ),
                    bidding_strategy=str(
                        (scm or {}).get("bidding_strategy")
                        or (fact or {}).get("bidding_strategy")
                        or "unknown"
                    ),
                    start_date=_as_date(
                        (scm or {}).get("start_date")
                        or (fact or {}).get("start_date")
                    ),
                    end_date=_as_date((scm or {}).get("end_date")),
                    daily_budget=(
                        _decimal((scm or {}).get("daily_budget"))
                        if (scm or {}).get("daily_budget") is not None
                        else (
                            _decimal((fact or {}).get("daily_budget"))
                            if (fact or {}).get("daily_budget") is not None
                            else None
                        )
                    ),
                    impressions=(fact or {}).get("impressions"),
                    clicks=(fact or {}).get("clicks"),
                    spend=(fact or {}).get("spend"),
                    orders=(fact or {}).get("orders"),
                    sales=(fact or {}).get("sales"),
                    top_of_search_share=(fact or {}).get("top_of_search_share"),
                    scm_matched=scm is not None,
                    has_metrics=fact is not None,
                )
            )
        return items

    def _filter_campaigns(
        self,
        items: list[RemoteCampaignOverviewMetric],
        *,
        enabled: bool | None,
        statuses: tuple[str, ...],
        targeting_type: str | None,
        search: str,
        metric_filters: tuple[dict[str, object], ...],
        exact_campaign_key: str | None,
    ) -> list[RemoteCampaignOverviewMetric]:
        normalized_search = search.strip().casefold()
        normalized_statuses = {value.casefold() for value in statuses}
        normalized_targeting = _normal_targeting_type(targeting_type)
        filtered: list[RemoteCampaignOverviewMetric] = []
        for item in items:
            state = item.state.strip().casefold()
            if exact_campaign_key is not None and item.campaign_key != exact_campaign_key:
                continue
            if enabled is not None and (state == "enabled") is not enabled:
                continue
            if normalized_statuses and state not in normalized_statuses:
                continue
            if targeting_type and _normal_targeting_type(item.targeting_type) != normalized_targeting:
                continue
            if normalized_search and normalized_search not in " ".join(
                (item.campaign_name, item.reference_code, item.campaign_key)
            ).casefold():
                continue
            if not all(self._matches_metric_filter(item, rule) for rule in metric_filters):
                continue
            filtered.append(item)
        return filtered

    @staticmethod
    def _metric_value(
        item: RemoteCampaignOverviewMetric, field: str
    ) -> Decimal | None:
        if not item.has_metrics:
            return None
        if field == "impressions":
            return Decimal(item.impressions or 0)
        if field == "clicks":
            return Decimal(item.clicks or 0)
        if field == "spend":
            return _decimal(item.spend)
        if field == "orders":
            return Decimal(item.orders or 0)
        formulas = calculate_metrics(
            impressions=item.impressions or 0,
            clicks=item.clicks or 0,
            spend=item.spend or 0,
            orders=item.orders or 0,
            sales=item.sales or 0,
        )
        return formulas.get(field)

    def _matches_metric_filter(
        self, item: RemoteCampaignOverviewMetric, rule: dict[str, object]
    ) -> bool:
        field = str(rule["field"])
        operator = str(rule["operator"])
        if field not in METRIC_FILTER_FIELDS or operator not in METRIC_FILTER_OPERATORS:
            return False
        actual = self._metric_value(item, field)
        if actual is None:
            return False
        value = Decimal(str(rule["value"]))
        if operator == "gte":
            return actual >= value
        if operator == "lte":
            return actual <= value
        if operator == "eq":
            return actual == value
        value2 = Decimal(str(rule["value2"]))
        return value <= actual <= value2

    @classmethod
    def _order_campaigns(
        cls, items: list[RemoteCampaignOverviewMetric], *, ordering: str
    ) -> list[RemoteCampaignOverviewMetric]:
        descending = ordering.startswith("-")
        field = ordering.removeprefix("-")

        def value(item: RemoteCampaignOverviewMetric):
            fields = {
                "name": item.campaign_name.casefold(),
                "targetingType": _normal_targeting_type(item.targeting_type),
                "status": item.state.casefold(),
                "biddingStrategy": item.bidding_strategy.casefold(),
                "startDate": item.start_date,
                "endDate": item.end_date,
                "dailyBudget": item.daily_budget,
                "impressions": item.impressions,
                "spend": item.spend,
                "clicks": item.clicks,
                "ctr": cls._metric_value(item, "ctr"),
                "totalCost": item.spend,
                "orders": item.orders,
                "cpc": cls._metric_value(item, "cpc"),
                "acos": cls._metric_value(item, "acos"),
                "cvr": cls._metric_value(item, "cvr"),
            }
            return fields[field]

        present = [item for item in items if value(item) is not None]
        absent = [item for item in items if value(item) is None]
        present.sort(key=lambda item: (value(item), item.campaign_key), reverse=descending)
        absent.sort(key=lambda item: item.campaign_key)
        return [*present, *absent]

    @classmethod
    def _summary(
        cls,
        items: list[RemoteCampaignOverviewMetric],
    ) -> RemoteCampaignOverviewTotals | None:
        measured = [item for item in items if item.has_metrics]
        if not measured:
            return None
        return RemoteCampaignOverviewTotals(
            impressions=sum(int(item.impressions or 0) for item in measured),
            clicks=sum(int(item.clicks or 0) for item in measured),
            spend=sum((_decimal(item.spend) for item in measured), Decimal("0")),
            orders=sum(int(item.orders or 0) for item in measured),
            sales=sum((_decimal(item.sales) for item in measured), Decimal("0")),
            top_of_search_share=cls._weighted_top_of_search_share(measured),
        )

    @staticmethod
    def _weighted_top_of_search_share(
        items: list[RemoteCampaignOverviewMetric],
    ) -> Decimal | None:
        weighted = [
            (item.top_of_search_share, int(item.impressions or 0))
            for item in items
            if item.top_of_search_share is not None
        ]
        if not weighted:
            return None
        impression_total = sum(impressions for _, impressions in weighted)
        if impression_total > 0:
            return sum(value * impressions for value, impressions in weighted) / Decimal(
                impression_total
            )
        return sum(value for value, _ in weighted) / Decimal(len(weighted))

    def _daily_totals(
        self,
        *,
        merchant_id: int,
        merchant_code: str,
        start_date: date,
        end_date: date,
        campaign_keys: list[str],
        mappings: RemoteCampaignFieldMappings,
    ) -> list[RemoteCampaignDailyTotals]:
        if not campaign_keys:
            return []
        placeholders = ", ".join(["%s"] * len(campaign_keys))
        cte = self._fact_cte(mappings)
        with self.analysis_connection.cursor() as cursor:
            cursor.execute(
                f"""
                {cte}
                SELECT business_date, SUM(impressions), SUM(clicks), SUM(spend),
                       SUM(orders), SUM(sales)
                FROM selected_facts
                WHERE campaign_key IN ({placeholders})
                GROUP BY business_date
                ORDER BY business_date
                """,
                [
                    *self._fact_parameters(
                        merchant_id=merchant_id,
                        merchant_code=merchant_code,
                        start_date=start_date,
                        end_date=end_date,
                    ),
                    *campaign_keys,
                ],
            )
            rows = cursor.fetchall()
        return [
            RemoteCampaignDailyTotals(
                report_date=row[0],
                impressions=int(row[1] or 0),
                clicks=int(row[2] or 0),
                spend=_decimal(row[3]),
                orders=int(row[4] or 0),
                sales=_decimal(row[5]),
            )
            for row in rows
        ]
