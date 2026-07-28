from typing import BinaryIO, Iterable, NoReturn

from integrations.storage.base import (
    FileStorageUnavailable,
    StoredFile,
)


class ObjectStorageFileStorage:
    """Reserved object-storage adapter boundary; it performs no network calls in V1."""

    capability = {"available": False, "mode": "reserved", "code": "OBJECT_STORAGE"}
    timeout_seconds = 30
    max_retries = 2

    def _unavailable(self) -> NoReturn:
        raise FileStorageUnavailable(
            "Object storage is reserved and has no configured endpoint in V1"
        )

    def save_stream(
        self, *, namespace: str, filename: str, chunks: Iterable[bytes]
    ) -> StoredFile:
        self._unavailable()

    def open_binary(self, path: str) -> BinaryIO:
        self._unavailable()

    def write_bytes(
        self, *, namespace: str, filename: str, content: bytes
    ) -> str:
        self._unavailable()
