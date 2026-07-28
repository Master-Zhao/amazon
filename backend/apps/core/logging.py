import json
import logging
from datetime import UTC, datetime

from apps.core.request_context import current_request_id


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        request = getattr(record, "request", None)
        request_id = getattr(record, "request_id", None)
        if request_id is None and request is not None:
            request_id = getattr(request, "request_id", None)
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "requestId": request_id or current_request_id(),
        }
        for field in (
            "event",
            "dependency",
            "dependency_status",
            "http_method",
            "http_path",
            "status_code",
        ):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exceptionType"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False)
