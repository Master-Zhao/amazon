import hashlib
import re
import uuid
from pathlib import Path

from django.conf import settings

from integrations.storage.base import StoredFile

_SAFE_SUFFIX = re.compile(r"^\.[a-zA-Z0-9]{1,8}$")


class LocalFileStorage:
    timeout_seconds = 0
    max_retries = 0

    def __init__(self, root: Path | None = None):
        self.root = Path(root or settings.MEDIA_ROOT).resolve()

    def _path(self, namespace: str, filename: str) -> Path:
        directory = (self.root / namespace).resolve()
        if self.root not in directory.parents and directory != self.root:
            raise ValueError("Invalid storage namespace")
        directory.mkdir(parents=True, exist_ok=True)
        return directory / filename

    def save_stream(self, *, namespace: str, filename: str, chunks) -> StoredFile:
        suffix = Path(filename).suffix.lower()
        if not _SAFE_SUFFIX.match(suffix):
            suffix = ".bin"
        relative = f"{namespace}/{uuid.uuid4().hex}{suffix}"
        target = self._path(namespace, Path(relative).name)
        digest = hashlib.sha256()
        size = 0
        try:
            with target.open("wb") as handle:
                for chunk in chunks:
                    if not chunk:
                        continue
                    handle.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return StoredFile(relative, size, digest.hexdigest())

    def open_binary(self, path: str):
        target = (self.root / path).resolve()
        if self.root not in target.parents:
            raise ValueError("Invalid storage path")
        return target.open("rb")

    def write_bytes(self, *, namespace: str, filename: str, content: bytes) -> str:
        target = self._path(namespace, filename)
        target.write_bytes(content)
        return f"{namespace}/{filename}"
