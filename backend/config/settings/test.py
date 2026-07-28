from config.settings.base import *  # noqa: F403
from config.settings.environment import env, env_bool, mysql_database_config

SECRET_KEY = "test-only-secret-key"
DEBUG = False

if env_bool("USE_MYSQL_TESTS", False):
    DATABASES = {"default": mysql_database_config()}
    DATABASES["default"]["TEST"] = {
        "NAME": env("DB_TEST_NAME", DATABASES["default"]["NAME"]),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": env("SQLITE_TEST_DB", str(BASE_DIR / "test.sqlite3")),  # noqa: F405
        }
    }

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
REQUIRED_CONFIGURATION_KEYS = ()
