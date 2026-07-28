import json
import os
import subprocess
import sys
from pathlib import Path

from django.conf import settings

BACKEND_DIR = Path(__file__).resolve().parents[1]


def run_settings_import(module: str, overrides: dict[str, str | None]):
    environment = os.environ.copy()
    for name, value in overrides.items():
        if value is None:
            environment.pop(name, None)
        else:
            environment[name] = value
    script = (
        "import json, importlib; "
        f"s=importlib.import_module('{module}'); "
        "print(json.dumps({"
        "'debug': s.DEBUG, "
        "'sessionSecure': s.SESSION_COOKIE_SECURE, "
        "'csrfSameSite': s.CSRF_COOKIE_SAMESITE, "
        "'jwtAccessMinutes': s.JWT_ACCESS_TOKEN_TTL_MINUTES, "
        "'jwtRefreshDays': s.JWT_REFRESH_TOKEN_TTL_DAYS, "
        "'jwtCookieName': s.JWT_REFRESH_COOKIE_NAME, "
        "'jwtCookiePath': s.JWT_REFRESH_COOKIE_PATH, "
        "'jwtCookieSecure': s.JWT_COOKIE_SECURE, "
        "'jwtCookieHttpOnly': s.JWT_COOKIE_HTTP_ONLY, "
        "'jwtCookieSameSite': s.JWT_COOKIE_SAME_SITE, "
        "'jwtRotate': s.JWT_ROTATE_REFRESH_TOKENS, "
        "'jwtBlacklist': s.JWT_BLACKLIST_AFTER_ROTATION"
        "}))"
    )
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_explicit_test_settings_are_loaded():
    assert settings.SETTINGS_MODULE == "config.settings.test"
    assert settings.DEBUG is False
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert settings.DEFAULT_AUTO_FIELD == "django.db.models.BigAutoField"
    assert settings.JWT_COOKIE_HTTP_ONLY is True
    assert settings.JWT_COOKIE_SECURE is False
    assert settings.JWT_COOKIE_SAME_SITE == "Lax"


def test_phase_one_does_not_install_business_apps():
    forbidden_apps = {
        "apps.tenants",
        "apps.permissions",
        "apps.stores",
        "apps.reports",
        "apps.advertising",
        "apps.analytics",
        "apps.agents",
        "apps.recommendations",
        "apps.actions",
    }
    assert forbidden_apps.isdisjoint(settings.INSTALLED_APPS)


def test_local_settings_load_and_explicitly_parse_debug():
    result = run_settings_import(
        "config.settings.local",
        {
            "DJANGO_DEBUG": "false",
            "JWT_ACCESS_TOKEN_TTL_MINUTES": "20",
        },
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["debug"] is False
    assert payload["jwtAccessMinutes"] == 20
    assert payload["jwtCookieHttpOnly"] is True
    assert payload["jwtCookieSecure"] is False
    assert payload["jwtCookieSameSite"] == "Lax"


def test_prod_settings_load_with_complete_configuration_and_force_debug_off():
    sensitive_secret = "prod-test-secret-must-not-be-printed"
    result = run_settings_import(
        "config.settings.prod",
        {
            "DJANGO_SECRET_KEY": sensitive_secret,
            "DB_PASSWORD": "prod-test-db-password-must-not-be-printed",
            "DJANGO_ALLOWED_HOSTS": "example.invalid",
            "DJANGO_DEBUG": "true",
            "SESSION_COOKIE_SECURE": "true",
            "CSRF_COOKIE_SAMESITE": "Strict",
            "JWT_ACCESS_TOKEN_TTL_MINUTES": "10",
            "JWT_REFRESH_TOKEN_TTL_DAYS": "14",
            "JWT_REFRESH_COOKIE_NAME": "phase2_refresh",
            "JWT_REFRESH_COOKIE_PATH": "/api/v1/auth/",
            "JWT_COOKIE_SECURE": "true",
            "JWT_COOKIE_HTTP_ONLY": "true",
            "JWT_COOKIE_SAME_SITE": "Strict",
            "JWT_ROTATE_REFRESH_TOKENS": "false",
            "JWT_BLACKLIST_AFTER_ROTATION": "false",
        },
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "debug": False,
        "sessionSecure": True,
        "csrfSameSite": "Strict",
        "jwtAccessMinutes": 10,
        "jwtRefreshDays": 14,
        "jwtCookieName": "phase2_refresh",
        "jwtCookiePath": "/api/v1/auth/",
        "jwtCookieSecure": True,
        "jwtCookieHttpOnly": True,
        "jwtCookieSameSite": "Strict",
        "jwtRotate": False,
        "jwtBlacklist": False,
    }
    assert sensitive_secret not in result.stdout + result.stderr
    assert "prod-test-db-password-must-not-be-printed" not in result.stdout + result.stderr


def test_prod_settings_fail_clearly_when_required_configuration_is_missing():
    result = run_settings_import(
        "config.settings.prod",
        {
            "DJANGO_SECRET_KEY": None,
            "DB_PASSWORD": None,
            "DJANGO_ALLOWED_HOSTS": None,
        },
    )

    assert result.returncode != 0
    assert "Missing required production configuration" in result.stderr
    assert "DJANGO_SECRET_KEY" in result.stderr


def test_invalid_jwt_configuration_fails_without_exposing_values():
    invalid_value = "invalid-sensitive-samesite-value"
    result = run_settings_import(
        "config.settings.local",
        {"JWT_COOKIE_SAME_SITE": invalid_value},
    )

    assert result.returncode != 0
    assert "JWT_COOKIE_SAME_SITE must be one of" in result.stderr
    assert invalid_value not in result.stdout + result.stderr


def test_prod_settings_reject_insecure_refresh_cookie():
    result = run_settings_import(
        "config.settings.prod",
        {
            "DJANGO_SECRET_KEY": "prod-test-secret",
            "DB_PASSWORD": "prod-test-password",
            "DJANGO_ALLOWED_HOSTS": "example.invalid",
            "JWT_COOKIE_SECURE": "false",
            "JWT_COOKIE_HTTP_ONLY": "true",
        },
    )

    assert result.returncode != 0
    assert "JWT_COOKIE_SECURE must be true in production" in result.stderr


def test_prod_settings_reject_script_readable_refresh_cookie():
    result = run_settings_import(
        "config.settings.prod",
        {
            "DJANGO_SECRET_KEY": "prod-test-secret",
            "DB_PASSWORD": "prod-test-password",
            "DJANGO_ALLOWED_HOSTS": "example.invalid",
            "JWT_COOKIE_SECURE": "true",
            "JWT_COOKIE_HTTP_ONLY": "false",
        },
    )

    assert result.returncode != 0
    assert "JWT_COOKIE_HTTP_ONLY must be true in production" in result.stderr
