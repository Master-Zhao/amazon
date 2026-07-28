from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ReportSourceCapability:
    code: str
    available: bool
    mode: str


@dataclass(frozen=True, slots=True)
class ReportFetchRequest:
    tenant_id: str
    profile_id: str
    report_type: str
    start_date: date
    end_date: date
    idempotency_key: str
    existing_storage_path: str = ""


@dataclass(frozen=True, slots=True)
class ReportFetchResult:
    storage_path: str
    external_request_id: str


class ReportSourceError(RuntimeError):
    retryable = False


class ReportSourceUnavailable(ReportSourceError):
    pass


class ReportSourceTimeout(ReportSourceError):
    retryable = True


class ReportSource(Protocol):
    capability: ReportSourceCapability
    timeout_seconds: int
    max_retries: int

    def fetch(self, request: ReportFetchRequest) -> ReportFetchResult: ...


class FileUploadReportSource:
    capability = ReportSourceCapability("FILE_UPLOAD", True, "implemented")
    timeout_seconds = 0
    max_retries = 0

    def fetch(self, request: ReportFetchRequest) -> ReportFetchResult:
        if not request.existing_storage_path:
            raise ReportSourceError("File upload source requires an existing storage path")
        return ReportFetchResult(
            storage_path=request.existing_storage_path,
            external_request_id=request.idempotency_key,
        )


class ThirdPartyProviderReportSource:
    capability = ReportSourceCapability("THIRD_PARTY_PROVIDER", False, "reserved")
    timeout_seconds = 30
    max_retries = 2

    def fetch(self, request: ReportFetchRequest) -> ReportFetchResult:
        raise ReportSourceUnavailable(
            "Third-party report provider is reserved and has no configured connector"
        )


class AmazonAdsApiReportSource:
    capability = ReportSourceCapability("AMAZON_ADS_API", False, "reserved")
    timeout_seconds = 30
    max_retries = 2

    def fetch(self, request: ReportFetchRequest) -> ReportFetchResult:
        raise ReportSourceUnavailable(
            "Amazon Ads report API is reserved and cannot make real requests in V1"
        )
