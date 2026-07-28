import os
from collections.abc import Iterable

from django.core.exceptions import ImproperlyConfigured


def env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ImproperlyConfigured(f"{name} must be a boolean value")


def env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    try:
        return int(raw_value) if raw_value is not None else default
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} must be an integer") from exc


def env_positive_int(name: str, default: int) -> int:
    value = env_int(name, default)
    if value <= 0:
        raise ImproperlyConfigured(f"{name} must be greater than zero")
    return value


def env_choice(name: str, default: str, choices: Iterable[str]) -> str:
    value = env(name, default)
    allowed = tuple(choices)
    if value not in allowed:
        raise ImproperlyConfigured(
            f"{name} must be one of: {', '.join(allowed)}"
        )
    return value


def env_list(name: str, default: Iterable[str] = ()) -> list[str]:
    raw_value = os.getenv(name)
    if raw_value is None:
        return list(default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def mysql_database_config() -> dict[str, object]:
    return {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME", "amazon_ads"),
        "USER": env("DB_USER", "amazon_ads"),
        "PASSWORD": env("DB_PASSWORD", ""),
        "HOST": env("DB_HOST", "127.0.0.1"),
        "PORT": env("DB_PORT", "3306"),
        "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
