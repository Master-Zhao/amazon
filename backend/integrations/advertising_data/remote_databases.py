from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from django.conf import settings
from django.db import connections
from rest_framework import status
from rest_framework.exceptions import APIException

from apps.core.errors import ErrorCode

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
    impressions: int | None
    clicks: int | None
    spend: Decimal | None
    orders: int | None
    sales: Decimal | None
    top_of_search_share: Decimal | None
    scm_matched: bool
    has_metrics: bool = True


@dataclass(frozen=True, slots=True)
class RemoteCampaignOverviewTotals:
    impressions: int
    clicks: int
    spend: Decimal
    orders: int
    sales: Decimal
    top_of_search_share: Decimal | None


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
    history_through_date: date | None = None
    realtime_through_date: date | None = None
    realtime_as_of: datetime | None = None
    deduplication_version: str = "legacy-history-only"
    field_mappings: dict[str, str] | None = None


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

    def _aggregate_reader(self):
        scm_connection, analysis_connection = self._connections()
        from .remote_campaign_aggregates import RemoteCampaignAggregateReader

        return RemoteCampaignAggregateReader(
            scm_connection=scm_connection,
            analysis_connection=analysis_connection,
        )

    def campaign_metrics(
        self,
        *,
        merchant_id: int,
        merchant_code: str,
        start_date: date | None,
        end_date: date | None,
    ) -> list[RemoteCampaignMetric]:
        return self._aggregate_reader().campaign_metrics(
            merchant_id=merchant_id,
            merchant_code=merchant_code,
            start_date=start_date,
            end_date=end_date,
        )

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
    ) -> RemoteCampaignOverviewPage:
        return self._aggregate_reader().campaign_overview(
            merchant_id=merchant_id,
            merchant_code=merchant_code,
            start_date=start_date,
            end_date=end_date,
            enabled=enabled,
            statuses=statuses,
            targeting_type=targeting_type,
            search=search,
            metric_filters=metric_filters,
            ordering=ordering,
            page=page,
            page_size=page_size,
            include_summary=include_summary,
            require_metrics=require_metrics,
        )

    def campaign_detail(
        self,
        *,
        merchant_id: int,
        merchant_code: str,
        campaign_key: str,
        start_date: date | None,
        end_date: date | None,
    ) -> RemoteCampaignOverviewPage:
        return self._aggregate_reader().campaign_overview(
            merchant_id=merchant_id,
            merchant_code=merchant_code,
            start_date=start_date,
            end_date=end_date,
            enabled=None,
            statuses=(),
            targeting_type=None,
            search="",
            metric_filters=(),
            ordering="name",
            page=1,
            page_size=1,
            include_summary=True,
            exact_campaign_key=campaign_key,
        )

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
        return self._aggregate_reader().update_campaign_enabled(
            merchant_id=merchant_id,
            merchant_code=merchant_code,
            campaign_key=campaign_key,
            enabled=enabled,
            campaign_name=campaign_name,
            targeting_type=targeting_type,
            daily_budget=daily_budget,
            bidding_strategy=bidding_strategy,
            start_date=start_date,
            end_date=end_date,
            actor_id=actor_id,
            actor_name=actor_name,
        )

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
        return self._aggregate_reader().create_campaign(
            merchant_id=merchant_id,
            merchant_code=merchant_code,
            name=name,
            targeting_type=targeting_type,
            daily_budget=daily_budget,
            bidding_strategy=bidding_strategy,
            start_date=start_date,
            end_date=end_date,
            enabled=enabled,
            actor_id=actor_id,
            actor_name=actor_name,
        )
