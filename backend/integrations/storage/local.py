from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from django.conf import settings


class LocalFileStorage:
    def __init__(self, root: Path | None = None):
        self.root = Path(root or settings.REPORT_STORAGE_ROOT).resolve()

    def _path(self, key: str) -> Path:
        normalized = PurePosixPath(key)
        if normalized.is_absolute() or ".." in normalized.parts:
            raise ValueError("Unsafe storage key")
        target = (self.root / Path(*normalized.parts)).resolve()
        if self.root != target and self.root not in target.parents:
            raise ValueError("Storage key escapes configured root")
        return target

    def save(self, *, key: str, chunks: Iterable[bytes]) -> int:
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        with target.open("xb") as output:
            for chunk in chunks:
                output.write(chunk)
                size += len(chunk)
        return size

    def open(self, *, key: str) -> BinaryIO:
        return self._path(key).open("rb")

    def exists(self, *, key: str) -> bool:
        return self._path(key).is_file()

    def delete(self, *, key: str) -> None:
        target = self._path(key)
        if target.is_file():
            target.unlink()
