import logging
from dataclasses import dataclass, field
from typing import Mapping, Protocol


@dataclass(frozen=True, slots=True)
class MonitoringEvent:
    name: str
    value: float = 1
    tags: Mapping[str, str] = field(default_factory=dict)


class MonitoringSink(Protocol):
    def emit(self, event: MonitoringEvent) -> None: ...


class LoggingMonitoringSink:
    """Safe baseline sink; production exporters implement MonitoringSink."""

    def __init__(self, logger_name: str = "apps.monitoring"):
        self.logger = logging.getLogger(logger_name)

    def emit(self, event: MonitoringEvent) -> None:
        self.logger.info(
            "Monitoring event",
            extra={
                "event": "monitoring_event",
                "metric_name": event.name,
                "metric_value": event.value,
                "metric_tags": dict(event.tags),
            },
        )
