from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *  # noqa: F403
from config.settings.environment import env, env_bool

DEBUG = False

required_values = {
    "DJANGO_SECRET_KEY": env("DJANGO_SECRET_KEY"),
    "DB_PASSWORD": env("DB_PASSWORD"),
    "DJANGO_ALLOWED_HOSTS": env("DJANGO_ALLOWED_HOSTS"),
}
missing_values = [name for name, value in required_values.items() if not value]
if missing_values:
    raise ImproperlyConfigured(
        "Missing required production configuration: " + ", ".join(missing_values)
    )

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
