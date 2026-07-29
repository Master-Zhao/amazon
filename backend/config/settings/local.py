from config.settings.base import *  # noqa: F403
from config.settings.environment import env_bool, env

DEBUG = env_bool("DJANGO_DEBUG", True)

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

REDIS_AVAILABLE = False
try:
    import redis as _redis

    _r = _redis.Redis.from_url(env("REDIS_URL", "redis://127.0.0.1:6379/0"))
    _r.ping()
    _r.close()
    REDIS_AVAILABLE = True
except Exception:
    pass

if not REDIS_AVAILABLE:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "amazon-ads-v1",
            "KEY_PREFIX": CACHE_KEY_PREFIX,
            "TIMEOUT": 300,
        }
    }
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"
