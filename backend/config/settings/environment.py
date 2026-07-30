import os
from collections.abc import Iterable
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


def load_env_file(path: Path) -> None:
    """Load a local dotenv file without replacing explicit process settings."""
    if not path.is_file():
        return

    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        key, separator, value = stripped.partition("=")
        key = key.strip()
        if not separator or not key:
            continue

        value = value.strip()
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {'"', "'"}
        ):
            value = value[1:-1]
        os.environ.setdefault(key, value)


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


def remote_mysql_database_config(prefix: str) -> dict[str, object]:
    required_names = (
        f"{prefix}_DB_NAME",
        f"{prefix}_DB_USER",
        f"{prefix}_DB_PASSWORD",
        f"{prefix}_DB_HOST",
        f"{prefix}_DB_PORT",
    )
    values = {name: env(name) for name in required_names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ImproperlyConfigured(
            "Missing remote database configuration: " + ", ".join(missing)
        )
    return {
        "ENGINE": "django.db.backends.mysql",
        "NAME": values[f"{prefix}_DB_NAME"],
        "USER": values[f"{prefix}_DB_USER"],
        "PASSWORD": values[f"{prefix}_DB_PASSWORD"],
        "HOST": values[f"{prefix}_DB_HOST"],
        "PORT": values[f"{prefix}_DB_PORT"],
        "CONN_MAX_AGE": env_int(f"{prefix}_DB_CONN_MAX_AGE", 60),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET SESSION TRANSACTION READ ONLY",
        },
    }
