import logging
import os

import redis
from django.conf import settings
from django.db import connections

from apps.core.request_context import current_request_id

logger = logging.getLogger(__name__)


def check_database() -> tuple[bool, str]:
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True, "available"
    except Exception:
        return False, "unavailable"


def check_redis() -> tuple[bool, str]:
    try:
        client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        client.ping()
        return True, "available"
    except (redis.RedisError, OSError, ValueError):
        return False, "unavailable"


def check_required_configuration() -> tuple[bool, str]:
    missing = [
        key
        for key in settings.REQUIRED_CONFIGURATION_KEYS
        if not os.getenv(key)
    ]
    if missing:
        return False, "missing:" + ",".join(sorted(missing))
    return True, "available"


def readiness_status() -> tuple[bool, dict[str, str]]:
    checks = {
        "database": check_database(),
        "redis": check_redis(),
        "configuration": check_required_configuration(),
    }
    for dependency, (available, detail) in checks.items():
        if not available:
            logger.warning(
                "Readiness dependency unavailable",
                extra={
                    "event": "readiness_check_failed",
                    "dependency": dependency,
                    "dependency_status": detail,
                    "request_id": current_request_id(),
                },
            )
    ready = all(result[0] for result in checks.values())
    return ready, {name: result[1] for name, result in checks.items()}
