from typing import BinaryIO, Protocol

from integrations.storage.base import FileStorage


class ReportSource(Protocol):
    def open(self) -> BinaryIO: ...


class FileUploadReportSource:
    def __init__(self, *, storage: FileStorage, storage_key: str):
        self.storage = storage
        self.storage_key = storage_key

    def open(self) -> BinaryIO:
        return self.storage.open(key=self.storage_key)


class ThirdPartyReportSource:
    def open(self) -> BinaryIO:
        raise NotImplementedError("Third-party report sources are outside V1")


class AmazonAdsApiReportSource:
    def open(self) -> BinaryIO:
        raise NotImplementedError("Amazon Ads API calls are outside V1")
