from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReportSourceCapability:
    code: str
    available: bool
    mode: str


class FileUploadReportSource:
    capability = ReportSourceCapability("FILE_UPLOAD", True, "implemented")


class ThirdPartyProviderReportSource:
    capability = ReportSourceCapability("THIRD_PARTY_PROVIDER", False, "reserved")


class AmazonAdsApiReportSource:
    capability = ReportSourceCapability("AMAZON_ADS_API", False, "reserved")

