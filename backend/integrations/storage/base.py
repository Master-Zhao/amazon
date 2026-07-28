from dataclasses import dataclass
from typing import BinaryIO, Iterable, Protocol


@dataclass(frozen=True, slots=True)
class StoredFile:
    path: str
    size_bytes: int
    sha256: str


class FileStorage(Protocol):
    def save_stream(self, *, namespace: str, filename: str, chunks: Iterable[bytes]) -> StoredFile: ...

    def open_binary(self, path: str) -> BinaryIO: ...

    def write_bytes(self, *, namespace: str, filename: str, content: bytes) -> str: ...

