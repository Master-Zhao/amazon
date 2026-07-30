import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import DatabaseError, connections
from rest_framework import status
from rest_framework.exceptions import APIException

from apps.core.errors import ErrorCode

logger = logging.getLogger(__name__)

SCM_ALIAS = "scm_remote"
ANALYSIS_ALIAS = "ads_analysis_remote"


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


def remote_scope_for_profile(external_profile_id: str) -> RemoteAdvertisingScope:
    mapping = settings.REMOTE_AD_PROFILE_MERCHANT_MAP.get(external_profile_id)
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
