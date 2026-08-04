import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import DatabaseError, connections
from rest_framework import status
from rest_framework.exceptions import APIException

from apps.core.errors import ErrorCode

logger = logging.getLogger(__name__)

SCM_ALIAS = "scm_remote"
ANALYSIS_ALIAS = "ads_analysis_remote"


def _as_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    return value if isinstance(value, date) else None


class RemoteAdvertisingDataUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "远程广告数据源暂不可用"
    default_code = "remote_advertising_data_unavailable"
    error_code = ErrorCode.SERVICE_NOT_READY


class RemoteAdvertisingProfileNotMapped(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "当前 Profile 尚未配置远程商户与店铺编码映射"
    default_code = "remote_advertising_profile_not_mapped"
    error_code = ErrorCode.SERVICE_NOT_READY


@dataclass(frozen=True, slots=True)
class RemoteCampaignMetric:
    report_date: date
    external_campaign_id: str
    campaign_name: str
    impressions: int
    clicks: int
    spend: Decimal
    orders: int
    sales: Decimal
    daily_budget: Decimal | None
    state: str
    scm_matched: bool


@dataclass(frozen=True, slots=True)
class RemoteAdvertisingScope:
    merchant_id: int
    merchant_code: str


@dataclass(frozen=True, slots=True)
class RemoteCampaignOverviewMetric:
    campaign_key: str
    reference_code: str
    campaign_name: str
    targeting_type: str
    state: str
    bidding_strategy: str
    start_date: date | None
    end_date: date | None
    daily_budget: Decimal | None
    impressions: int
    clicks: int
    spend: Decimal
    orders: int
    sales: Decimal
    scm_matched: bool


@dataclass(frozen=True, slots=True)
class RemoteCampaignOverviewTotals:
    impressions: int
    clicks: int
    spend: Decimal
    orders: int
    sales: Decimal


@dataclass(frozen=True, slots=True)
class RemoteCampaignDailyTotals:
    report_date: date
    impressions: int
    clicks: int
    spend: Decimal
    orders: int
    sales: Decimal


@dataclass(frozen=True, slots=True)
class RemoteCampaignRiskMetric:
    campaign_key: str
    impressions: int
    clicks: int
    spend: Decimal
    orders: int
    sales: Decimal


@dataclass(frozen=True, slots=True)
class RemoteCampaignOverviewPage:
    items: list[RemoteCampaignOverviewMetric]
    summary: RemoteCampaignOverviewTotals | None
    page: int
    page_size: int
    total: int
    start_date: date | None
    end_date: date | None
    data_through_date: date | None
    trend: list[RemoteCampaignDailyTotals]
    risk_metrics: list[RemoteCampaignRiskMetric]


def remote_scope_for_profile(profile) -> RemoteAdvertisingScope:
    from apps.stores.models import AdvertisingProfileRemoteScope

    stored = AdvertisingProfileRemoteScope.objects.filter(
        profile=profile,
        is_active=True,
    ).first()
    if stored is not None:
        try:
            return RemoteAdvertisingScope(
                merchant_id=int(stored.external_merchant_id),
                merchant_code=stored.merchant_code.strip(),
            )
        except (TypeError, ValueError) as exc:
            raise RemoteAdvertisingProfileNotMapped(
                "当前 Profile 的远程商户映射无效"
            ) from exc

    mapping = settings.REMOTE_AD_PROFILE_MERCHANT_MAP.get(
        profile.external_profile_id
    )
    if mapping is None:
        raise RemoteAdvertisingProfileNotMapped()
    return RemoteAdvertisingScope(
        merchant_id=int(mapping["merchantId"]),
        merchant_code=str(mapping["merchantCode"]).strip(),
    )


class RemoteAdvertisingDataReader:
    def _connections(self):
        missing = [
            alias
            for alias in (SCM_ALIAS, ANALYSIS_ALIAS)
            if alias not in settings.DATABASES
        ]
        if missing:
            raise RemoteAdvertisingDataUnavailable(
                "远程广告数据库未启用或连接配置不完整"
            )
        return connections[SCM_ALIAS], connections[ANALYSIS_ALIAS]

    def campaign_metrics(
        self,
        *,
        merchant_id: int,
        merchant_code: str,
        start_date: date | None,
        end_date: date | None,
    ) -> list[RemoteCampaignMetric]:
        scm_connection, analysis_connection = self._connections()
        try:
            effective_start, effective_end = self._effective_dates(
                analysis_connection=analysis_connection,
                merchant_id=merchant_id,
                merchant_code=merchant_code,
                start_date=start_date,
                end_date=end_date,
            )
            if effective_start is None or effective_end is None:
                return []
            rows = self._analysis_rows(
                analysis_connection=analysis_connection,
                merchant_id=merchant_id,
                merchant_code=merchant_code,
                start_date=effective_start,
                end_date=effective_end,
            )
            scm_rows = self._scm_campaign_rows(
                scm_connection=scm_connection,
                merchant_id=merchant_id,
                merchant_code=merchant_code,
                analysis_rows=rows,
            )
        except DatabaseError as exc:
            logger.exception(
                "Remote advertising database query failed",
                extra={
                    "merchant_id": merchant_id,
                    "merchant_code": merchant_code,
                },
            )
            raise RemoteAdvertisingDataUnavailable() from exc

        metrics: list[RemoteCampaignMetric] = []
        for row in rows:
            external_id = str(row[1])
            scm = scm_rows.get(external_id)
            metrics.append(
                RemoteCampaignMetric(
                    report_date=row[0],
                    external_campaign_id=external_id,
                    campaign_name=(
                        str(scm["name"])
                        if scm and scm["name"]
                        else str(row[2] or external_id)
                    ),
                    impressions=int(row[3] or 0),
                    clicks=int(row[4] or 0),
                    spend=Decimal(str(row[5] or 0)),
                    orders=int(row[6] or 0),
                    sales=Decimal(str(row[7] or 0)),
                    daily_budget=(
                        Decimal(str(scm["budget"]))
                        if scm and scm["budget"] is not None
                        else (
                            Decimal(str(row[8])) if row[8] is not None else None
                        )
                    ),
                    state=(
                        str(scm["state"])
                        if scm and scm["state"]
                        else str(row[9] or "unknown")
                    ),
                    scm_matched=scm is not None,
                )
            )
        return metrics

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
        ordering: str,
        page: int,
        page_size: int,
        include_summary: bool,
    ) -> RemoteCampaignOverviewPage:
        scm_connection, analysis_connection = self._connections()
        try:
            effective_start, effective_end, latest = self._overview_dates(
                analysis_connection=analysis_connection,
                merchant_id=merchant_id,
                merchant_code=merchant_code,
                start_date=start_date,
                end_date=end_date,
            )
            if effective_start is None or effective_end is None:
                return RemoteCampaignOverviewPage(
                    items=[],
                    summary=None,
                    page=page,
                    page_size=page_size,
                    total=0,
                    start_date=None,
                    end_date=None,
                    data_through_date=None,
                    trend=[],
                    risk_metrics=[],
                )

            matching_scm_keys = self._scm_search_keys(
                scm_connection=scm_connection,
                merchant_id=merchant_id,
                merchant_code=merchant_code,
                search=search,
            )
            base_sql, base_parameters = self._campaign_overview_base_sql(
                merchant_id=merchant_id,
                merchant_code=merchant_code,
                start_date=effective_start,
                end_date=effective_end,
            )
            filtered_sql, filtered_parameters = self._campaign_overview_filtered_sql(
                base_sql=base_sql,
                base_parameters=base_parameters,
                enabled=enabled,
                statuses=statuses,
                targeting_type=targeting_type,
                search=search,
                matching_scm_keys=matching_scm_keys,
            )
            total = self._campaign_overview_count(
                analysis_connection=analysis_connection,
                filtered_sql=filtered_sql,
                parameters=filtered_parameters,
            )
            rows = self._campaign_overview_page_rows(
                analysis_connection=analysis_connection,
                filtered_sql=filtered_sql,
                parameters=filtered_parameters,
                ordering=ordering,
                page=page,
                page_size=page_size,
            )
            summary = (
                self._campaign_overview_summary(
                    analysis_connection=analysis_connection,
                    filtered_sql=filtered_sql,
                    parameters=filtered_parameters,
                )
                if include_summary
                else None
            )
            trend = self._campaign_overview_trend(
                analysis_connection=analysis_connection,
                filtered_sql=filtered_sql,
                parameters=filtered_parameters,
                merchant_id=merchant_id,
                merchant_code=merchant_code,
                start_date=effective_start,
                end_date=effective_end,
            )
            risk_metrics = self._campaign_overview_risk_metrics(
                analysis_connection=analysis_connection,
                filtered_sql=filtered_sql,
                parameters=filtered_parameters,
            )
            scm_rows = self._scm_campaign_rows_for_keys(
                scm_connection=scm_connection,
                merchant_id=merchant_id,
                merchant_code=merchant_code,
                campaign_keys=[str(row[0]) for row in rows],
            )
        except DatabaseError as exc:
            logger.exception(
                "Remote Campaign overview query failed",
                extra={"merchant_id": merchant_id, "merchant_code": merchant_code},
            )
            raise RemoteAdvertisingDataUnavailable() from exc

        items: list[RemoteCampaignOverviewMetric] = []
        for row in rows:
            campaign_key = str(row[0])
            scm = scm_rows.get(campaign_key)
            items.append(
                RemoteCampaignOverviewMetric(
                    campaign_key=campaign_key,
                    reference_code=str(
                        (scm or {}).get("code") or row[1] or campaign_key
                    ),
                    campaign_name=str(
                        (scm or {}).get("name") or row[2] or campaign_key
                    ),
                    targeting_type=str(
                        (scm or {}).get("type") or row[3] or "unknown"
                    ),
                    state=str((scm or {}).get("state") or row[4] or "unknown"),
                    bidding_strategy=str(
                        (scm or {}).get("bidding_strategy")
                        or row[5]
                        or "unknown"
                    ),
                    start_date=_as_date((scm or {}).get("start_date")),
                    end_date=_as_date((scm or {}).get("end_date")),
                    daily_budget=(
                        Decimal(str((scm or {}).get("budget")))
                        if (scm or {}).get("budget") is not None
                        else (Decimal(str(row[6])) if row[6] is not None else None)
                    ),
                    impressions=int(row[7] or 0),
                    clicks=int(row[8] or 0),
                    spend=Decimal(str(row[9] or 0)),
                    orders=int(row[10] or 0),
                    sales=Decimal(str(row[11] or 0)),
                    scm_matched=scm is not None,
                )
            )
        return RemoteCampaignOverviewPage(
            items=items,
            summary=summary,
            page=page,
            page_size=page_size,
            total=total,
            start_date=effective_start,
            end_date=effective_end,
            data_through_date=latest,
            trend=trend,
            risk_metrics=risk_metrics,
        )

    def _overview_dates(
        self,
        *,
        analysis_connection,
        merchant_id: int,
        merchant_code: str,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[date | None, date | None, date | None]:
        with analysis_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT MAX(DATE(creation_date))
                FROM bi_analyze_ad_campaign
                WHERE mer_id = %s
                  AND mer_code = %s
                  AND creation_date IS NOT NULL
                """,
                [merchant_id, merchant_code],
            )
            latest = cursor.fetchone()[0]
        if latest is None:
            return None, None, None
        effective_end = end_date or latest
        effective_start = start_date or (effective_end - timedelta(days=29))
        return effective_start, effective_end, latest

    def _campaign_overview_base_sql(
        self,
        *,
        merchant_id: int,
        merchant_code: str,
        start_date: date,
        end_date: date,
    ) -> tuple[str, list[object]]:
        return (
            """
            SELECT
                COALESCE(CAST(campaign_id AS CHAR), campaign_code) AS campaign_key,
                MAX(campaign_code) AS reference_code,
                COALESCE(MAX(campaign_name), MAX(name), MAX(code)) AS campaign_name,
                MAX(campaign_type) AS targeting_type,
                MAX(campaign_state) AS campaign_state,
                MAX(campaign_bidding_strategy) AS bidding_strategy,
                MAX(campaign_daily_budget) AS daily_budget,
                SUM(COALESCE(imperssion, 0)) AS impressions,
                SUM(COALESCE(click, 0)) AS clicks,
                SUM(COALESCE(spend, 0)) AS spend,
                SUM(COALESCE(orders, 0)) AS orders,
                SUM(COALESCE(sales, 0)) AS sales
            FROM bi_analyze_ad_campaign
            WHERE mer_id = %s
              AND mer_code = %s
              AND creation_date IS NOT NULL
              AND DATE(creation_date) >= %s
              AND DATE(creation_date) <= %s
              AND COALESCE(CAST(campaign_id AS CHAR), campaign_code) IS NOT NULL
            GROUP BY COALESCE(CAST(campaign_id AS CHAR), campaign_code)
            """,
            [merchant_id, merchant_code, start_date, end_date],
        )

    def _campaign_overview_filtered_sql(
        self,
        *,
        base_sql: str,
        base_parameters: list[object],
        enabled: bool | None,
        statuses: tuple[str, ...],
        targeting_type: str | None,
        search: str,
        matching_scm_keys: list[str],
    ) -> tuple[str, list[object]]:
        clauses: list[str] = []
        parameters = list(base_parameters)
        if enabled is not None:
            clauses.append(
                "LOWER(COALESCE(campaign_state, 'unknown')) "
                + ("= 'enabled'" if enabled else "<> 'enabled'")
            )
        if statuses:
            placeholders = ", ".join(["%s"] * len(statuses))
            clauses.append(
                f"LOWER(COALESCE(campaign_state, 'unknown')) IN ({placeholders})"
            )
            parameters.extend(statuses)
        if targeting_type:
            clauses.append("LOWER(COALESCE(targeting_type, 'unknown')) = %s")
            parameters.append(targeting_type.lower())
        if search:
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            like = f"%{escaped}%"
            search_parts = [
                "campaign_name LIKE %s",
                "reference_code LIKE %s",
                "campaign_key LIKE %s",
            ]
            parameters.extend([like, like, like])
            if matching_scm_keys:
                placeholders = ", ".join(["%s"] * len(matching_scm_keys))
                search_parts.append(f"campaign_key IN ({placeholders})")
                parameters.extend(matching_scm_keys)
            clauses.append("(" + " OR ".join(search_parts) + ")")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        return f"SELECT * FROM ({base_sql}) AS campaign_scope{where}", parameters

    def _campaign_overview_count(
        self, *, analysis_connection, filtered_sql: str, parameters: list[object]
    ) -> int:
        with analysis_connection.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*) FROM ({filtered_sql}) AS filtered_campaigns",
                parameters,
            )
            return int(cursor.fetchone()[0] or 0)

    def _campaign_overview_page_rows(
        self,
        *,
        analysis_connection,
        filtered_sql: str,
        parameters: list[object],
        ordering: str,
        page: int,
        page_size: int,
    ) -> list[tuple]:
        descending = ordering.startswith("-")
        key = ordering.removeprefix("-")
        order_expressions = {
            "name": "campaign_name",
            "targetingType": "targeting_type",
            "status": "campaign_state",
            "biddingStrategy": "bidding_strategy",
            "dailyBudget": "daily_budget",
            "impressions": "impressions",
            "spend": "spend",
            "clicks": "clicks",
            "ctr": "CASE WHEN impressions = 0 THEN NULL ELSE clicks / impressions END",
            "totalCost": "spend",
            "orders": "orders",
            "cpc": "CASE WHEN clicks = 0 THEN NULL ELSE spend / clicks END",
            "acos": "CASE WHEN sales = 0 THEN NULL ELSE spend / sales END",
            "cvr": "CASE WHEN clicks = 0 THEN NULL ELSE orders / clicks END",
        }
        expression = order_expressions[key]
        direction = "DESC" if descending else "ASC"
        offset = (page - 1) * page_size
        with analysis_connection.cursor() as cursor:
            cursor.execute(
                f"""
                {filtered_sql}
                ORDER BY {expression} {direction}, campaign_key ASC
                LIMIT %s OFFSET %s
                """,
                [*parameters, page_size, offset],
            )
            return list(cursor.fetchall())

    def _campaign_overview_summary(
        self, *, analysis_connection, filtered_sql: str, parameters: list[object]
    ) -> RemoteCampaignOverviewTotals | None:
        with analysis_connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    SUM(impressions), SUM(clicks), SUM(spend),
                    SUM(orders), SUM(sales)
                FROM ({filtered_sql}) AS filtered_campaigns
                """,
                parameters,
            )
            row = cursor.fetchone()
        if row is None or row[0] is None:
            return None
        return RemoteCampaignOverviewTotals(
            impressions=int(row[0] or 0),
            clicks=int(row[1] or 0),
            spend=Decimal(str(row[2] or 0)),
            orders=int(row[3] or 0),
            sales=Decimal(str(row[4] or 0)),
        )

    def _campaign_overview_trend(
        self,
        *,
        analysis_connection,
        filtered_sql: str,
        parameters: list[object],
        merchant_id: int,
        merchant_code: str,
        start_date: date,
        end_date: date,
    ) -> list[RemoteCampaignDailyTotals]:
        with analysis_connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    DATE(source.creation_date),
                    SUM(COALESCE(source.imperssion, 0)),
                    SUM(COALESCE(source.click, 0)),
                    SUM(COALESCE(source.spend, 0)),
                    SUM(COALESCE(source.orders, 0)),
                    SUM(COALESCE(source.sales, 0))
                FROM bi_analyze_ad_campaign AS source
                INNER JOIN ({filtered_sql}) AS filtered_campaigns
                    ON COALESCE(CAST(source.campaign_id AS CHAR), source.campaign_code)
                       = filtered_campaigns.campaign_key
                WHERE source.mer_id = %s
                  AND source.mer_code = %s
                  AND DATE(source.creation_date) >= %s
                  AND DATE(source.creation_date) <= %s
                GROUP BY DATE(source.creation_date)
                ORDER BY DATE(source.creation_date)
                """,
                [
                    *parameters,
                    merchant_id,
                    merchant_code,
                    start_date,
                    end_date,
                ],
            )
            rows = cursor.fetchall()
        return [
            RemoteCampaignDailyTotals(
                report_date=row[0],
                impressions=int(row[1] or 0),
                clicks=int(row[2] or 0),
                spend=Decimal(str(row[3] or 0)),
                orders=int(row[4] or 0),
                sales=Decimal(str(row[5] or 0)),
            )
            for row in rows
        ]

    def _campaign_overview_risk_metrics(
        self, *, analysis_connection, filtered_sql: str, parameters: list[object]
    ) -> list[RemoteCampaignRiskMetric]:
        with analysis_connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT campaign_key, impressions, clicks, spend, orders, sales
                FROM ({filtered_sql}) AS filtered_campaigns
                ORDER BY campaign_key
                LIMIT 10001
                """,
                parameters,
            )
            rows = cursor.fetchall()
        if len(rows) > 10000:
            raise RemoteAdvertisingDataUnavailable(
                "当前筛选范围超过风险统计上限，请缩小日期或筛选范围"
            )
        return [
            RemoteCampaignRiskMetric(
                campaign_key=str(row[0]),
                impressions=int(row[1] or 0),
                clicks=int(row[2] or 0),
                spend=Decimal(str(row[3] or 0)),
                orders=int(row[4] or 0),
                sales=Decimal(str(row[5] or 0)),
            )
            for row in rows
        ]

    def _scm_search_keys(
        self,
        *,
        scm_connection,
        merchant_id: int,
        merchant_code: str,
        search: str,
    ) -> list[str]:
        if not search:
            return []
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"
        with scm_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT campaign_id, code
                FROM eb_ad_campaign
                WHERE mer_id = %s
                  AND mer_code = %s
                  AND (name LIKE %s OR code LIKE %s)
                ORDER BY update_time DESC, id DESC
                LIMIT %s
                """,
                [merchant_id, merchant_code, like, like, settings.REMOTE_AD_MAX_ROWS],
            )
            keys: list[str] = []
            for campaign_id, code in cursor.fetchall():
                for value in (campaign_id, code):
                    if value is not None and str(value) not in keys:
                        keys.append(str(value))
            return keys

    def _scm_campaign_rows_for_keys(
        self,
        *,
        scm_connection,
        merchant_id: int,
        merchant_code: str,
        campaign_keys: list[str],
    ) -> dict[str, dict[str, object]]:
        if not campaign_keys:
            return {}
        placeholders = ", ".join(["%s"] * len(campaign_keys))
        sql = f"""
            SELECT
                campaign_id, code, name, type, state, start_date, end_date,
                budget, bidding_strategy
            FROM eb_ad_campaign
            WHERE mer_id = %s
              AND mer_code = %s
              AND (
                CAST(campaign_id AS CHAR) IN ({placeholders})
                OR code IN ({placeholders})
              )
            ORDER BY update_time DESC, id DESC
        """
        parameters = [merchant_id, merchant_code, *campaign_keys, *campaign_keys]
        result: dict[str, dict[str, object]] = {}
        with scm_connection.cursor() as cursor:
            cursor.execute(sql, parameters)
            for row in cursor.fetchall():
                payload = {
                    "code": row[1],
                    "name": row[2],
                    "type": row[3],
                    "state": row[4],
                    "start_date": row[5],
                    "end_date": row[6],
                    "budget": row[7],
                    "bidding_strategy": row[8],
                }
                for value in (row[0], row[1]):
                    if value is not None:
                        result.setdefault(str(value), payload)
        return result

    def _effective_dates(
        self,
        *,
        analysis_connection,
        merchant_id: int,
        merchant_code: str,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[date | None, date | None]:
        if start_date is not None and end_date is not None:
            return start_date, end_date
        with analysis_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT MAX(DATE(creation_date))
                FROM bi_analyze_ad_campaign
                WHERE mer_id = %s
                  AND mer_code = %s
                  AND creation_date IS NOT NULL
                """,
                [merchant_id, merchant_code],
            )
            latest = cursor.fetchone()[0]
        if latest is None:
            return None, None
        return start_date or latest, end_date or latest

    def _analysis_rows(
        self,
        *,
        analysis_connection,
        merchant_id: int,
        merchant_code: str,
        start_date: date,
        end_date: date,
    ) -> list[tuple]:
        with analysis_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    DATE(creation_date) AS report_date,
                    COALESCE(CAST(campaign_id AS CHAR), campaign_code) AS campaign_key,
                    COALESCE(MAX(campaign_name), MAX(name), MAX(code)) AS campaign_name,
                    SUM(COALESCE(imperssion, 0)) AS impressions,
                    SUM(COALESCE(click, 0)) AS clicks,
                    SUM(COALESCE(spend, 0)) AS spend,
                    SUM(COALESCE(orders, 0)) AS orders,
                    SUM(COALESCE(sales, 0)) AS sales,
                    MAX(campaign_daily_budget) AS daily_budget,
                    MAX(campaign_state) AS campaign_state
                FROM bi_analyze_ad_campaign
                WHERE
                    mer_id = %s
                    AND mer_code = %s
                    AND creation_date IS NOT NULL
                    AND DATE(creation_date) >= %s
                    AND DATE(creation_date) <= %s
                    AND COALESCE(CAST(campaign_id AS CHAR), campaign_code) IS NOT NULL
                GROUP BY
                    DATE(creation_date),
                    COALESCE(CAST(campaign_id AS CHAR), campaign_code)
                ORDER BY report_date DESC, campaign_name, campaign_key
                LIMIT %s
                """,
                [
                    merchant_id,
                    merchant_code,
                    start_date,
                    end_date,
                    settings.REMOTE_AD_MAX_ROWS,
                ],
            )
            return list(cursor.fetchall())

    def _scm_campaign_rows(
        self,
        *,
        scm_connection,
        merchant_id: int,
        merchant_code: str,
        analysis_rows: list[tuple],
    ) -> dict[str, dict[str, object]]:
        campaign_keys = sorted({str(row[1]) for row in analysis_rows})
        if not campaign_keys:
            return {}
        placeholders = ", ".join(["%s"] * len(campaign_keys))
        sql = f"""
            SELECT campaign_id, code, name, state, budget
            FROM eb_ad_campaign
            WHERE mer_id = %s
              AND mer_code = %s
              AND (
                CAST(campaign_id AS CHAR) IN ({placeholders})
                OR code IN ({placeholders})
              )
            ORDER BY update_time DESC, id DESC
        """
        parameters = [
            merchant_id,
            merchant_code,
            *campaign_keys,
            *campaign_keys,
        ]
        result: dict[str, dict[str, object]] = {}
        with scm_connection.cursor() as cursor:
            cursor.execute(sql, parameters)
            for campaign_id, campaign_code, name, state, budget in cursor.fetchall():
                payload = {
                    "name": name,
                    "state": state,
                    "budget": budget,
                }
                for key in (campaign_id, campaign_code):
                    if key is not None:
                        result.setdefault(str(key), payload)
        return result
