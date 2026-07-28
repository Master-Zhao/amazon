from collections.abc import Iterable
from dataclasses import dataclass
from typing import BinaryIO, Protocol


class FileStorageUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StoredFile:
    path: str
    size_bytes: int
    sha256: str = ""


class FileStorage(Protocol):
    def save(self, *, key: str, chunks: Iterable[bytes]) -> int: ...

    def open(self, *, key: str) -> BinaryIO: ...

    def exists(self, *, key: str) -> bool: ...

    def delete(self, *, key: str) -> None: ...
