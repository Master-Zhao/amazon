"""Append-only, schema-validated, in-memory audit event collector."""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import uuid4

from .post_processor import utc_now
from .schema_loader import validate_audit_event

FORBIDDEN_METADATA_KEYS = {"access_token", "refresh_token", "authorization_header", "secret", "password"}


class AuditCollector:
    """Collect immutable audit dictionaries without credentials or prompt bodies."""

    def __init__(self, task: dict[str, Any]) -> None:
        self._task = task
        self._events: list[dict[str, Any]] = []
        self._step = 0
        trace_hash = hashlib.sha256(f"{task['task_id']}|{task['run_id']}".encode("utf-8")).hexdigest()
        self._trace_id = f"trace-{trace_hash[:16]}"

    @property
    def events(self) -> list[dict[str, Any]]:
        """Return a defensive copy of all append-only events."""

        return [dict(event) for event in self._events]

    def set_attempt_id(self, attempt_id: str) -> None:
        """Advance the mutable collector context while preserving prior events."""

        self._task["attempt_id"] = attempt_id

    def record(
        self,
        event_type: str,
        status_before: str | None,
        status_after: str,
        summary: str,
        *,
        plan_version: int = 0,
        error_code: str | None = None,
        metadata: dict[str, str | int | bool | None] | None = None,
    ) -> dict[str, Any]:
        """Append one validated audit event."""

        safe_metadata = dict(metadata or {})
        forbidden = FORBIDDEN_METADATA_KEYS.intersection(key.lower() for key in safe_metadata)
        if forbidden:
            raise ValueError(f"sensitive audit metadata keys are forbidden: {sorted(forbidden)}")
        self._step += 1
        event = {
            "schema_version": "2.0",
            "event_id": f"event-{uuid4().hex}",
            "task_id": self._task["task_id"],
            "run_id": self._task["run_id"],
            "attempt_id": self._task.get("attempt_id"),
            "step_id": f"step-{self._step:04d}",
            "trace_id": self._trace_id,
            "event_type": event_type,
            "occurred_at": utc_now(),
            "plan_version": plan_version,
            "data_snapshot_id": self._task["data_snapshot_id"],
            "status_before": status_before,
            "status_after": status_after,
            "summary": summary,
            "error_code": error_code,
            "metadata": safe_metadata,
        }
        validate_audit_event(event)
        self._events.append(event)
        return dict(event)
