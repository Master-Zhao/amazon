from pathlib import Path
from datetime import timedelta

from kombu import Queue

from django.core.exceptions import ImproperlyConfigured

from config.settings.environment import (
    env,
    env_bool,
    env_choice,
    env_int,
    env_list,
    env_positive_int,
    mysql_database_config,
)

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = env("DJANGO_SECRET_KEY", "unsafe-local-development-only")
DEBUG = False
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1"])

APP_VERSION = env("APP_VERSION", "0.1.0")
GIT_COMMIT = env("GIT_COMMIT", "unknown")
BUILD_TIME = env("BUILD_TIME", "unknown")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "apps.core",
    "apps.accounts",
    "apps.tenants",
    "apps.stores",
    "apps.permissions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "apps.core.middleware.RequestIdMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {"default": mysql_database_config()}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.User"

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", False)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", "Lax")

JWT_ACCESS_TOKEN_TTL_MINUTES = env_positive_int(
    "JWT_ACCESS_TOKEN_TTL_MINUTES", 15
)
JWT_REFRESH_TOKEN_TTL_DAYS = env_positive_int("JWT_REFRESH_TOKEN_TTL_DAYS", 7)
JWT_REFRESH_COOKIE_NAME = env("JWT_REFRESH_COOKIE_NAME", "refresh_token")
JWT_REFRESH_COOKIE_PATH = env("JWT_REFRESH_COOKIE_PATH", "/api/v1/auth/")
JWT_COOKIE_SECURE = env_bool("JWT_COOKIE_SECURE", False)
JWT_COOKIE_HTTP_ONLY = env_bool("JWT_COOKIE_HTTP_ONLY", True)
JWT_COOKIE_SAME_SITE = env_choice(
    "JWT_COOKIE_SAME_SITE", "Lax", ("Lax", "Strict", "None")
)
JWT_ROTATE_REFRESH_TOKENS = env_bool("JWT_ROTATE_REFRESH_TOKENS", True)
JWT_BLACKLIST_AFTER_ROTATION = env_bool("JWT_BLACKLIST_AFTER_ROTATION", True)

if not JWT_REFRESH_COOKIE_NAME:
    raise ImproperlyConfigured("JWT_REFRESH_COOKIE_NAME must not be empty")
if not JWT_REFRESH_COOKIE_PATH or not JWT_REFRESH_COOKIE_PATH.startswith("/"):
    raise ImproperlyConfigured("JWT_REFRESH_COOKIE_PATH must be an absolute path")
if JWT_COOKIE_SAME_SITE == "None" and not JWT_COOKIE_SECURE:
    raise ImproperlyConfigured(
        "JWT_COOKIE_SECURE must be true when JWT_COOKIE_SAME_SITE is None"
    )

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.authentication.AccessTokenAuthentication"
    ],
    "DEFAULT_RENDERER_CLASSES": ["apps.core.renderers.CamelCaseJSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "apps.core.parsers.CamelCaseJSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=JWT_ACCESS_TOKEN_TTL_MINUTES),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=JWT_REFRESH_TOKEN_TTL_DAYS),
    "ROTATE_REFRESH_TOKENS": JWT_ROTATE_REFRESH_TOKENS,
    "BLACKLIST_AFTER_ROTATION": JWT_BLACKLIST_AFTER_ROTATION,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "CHECK_USER_IS_ACTIVE": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Amazon Ads Optimizer API",
    "DESCRIPTION": (
        "V1 account authentication, tenant/store/profile context and permission APIs."
    ),
    "VERSION": APP_VERSION,
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

REDIS_URL = env("REDIS_URL", "redis://127.0.0.1:6379/0")
CELERY_BROKER_URL = env("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/1")
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_QUEUES = (
    Queue("default"),
    Queue("imports"),
    Queue("analysis"),
    Queue("maintenance"),
)
CELERY_TASK_ROUTES = {
    "apps.core.tasks.smoke_task": {"queue": "default"},
}
CELERY_TASK_TIME_LIMIT = env_int("CELERY_TASK_TIME_LIMIT", 30)
CELERY_TASK_SOFT_TIME_LIMIT = env_int("CELERY_TASK_SOFT_TIME_LIMIT", 20)
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_RESULT_EXPIRES = env_int("CELERY_RESULT_EXPIRES", 3600)
CELERY_BEAT_SCHEDULE: dict[str, object] = {}

REQUIRED_CONFIGURATION_KEYS = (
    "DJANGO_SECRET_KEY",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "REDIS_URL",
    "CELERY_BROKER_URL",
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "apps.core.logging.JsonLogFormatter"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    "loggers": {
        "django.server": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps.core.health": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
