# from pathlib import Path

# from config.settings.environment import env_bool, env, load_env_file

# load_env_file(Path(__file__).resolve().parents[3] / ".env")

# from config.settings.base import *  # noqa: E402,F403

# DEBUG = env_bool("DJANGO_DEBUG", True)

# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# REDIS_AVAILABLE = False
# try:
#     import redis as _redis

#     _r = _redis.Redis.from_url(env("REDIS_URL", "redis://127.0.0.1:6379/0"))
#     _r.ping()
#     _r.close()
#     REDIS_AVAILABLE = True
# except Exception:
#     pass

# if not REDIS_AVAILABLE:
#     CACHES = {
#         "default": {
#             "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
#             "LOCATION": "amazon-ads-v1",
#             "KEY_PREFIX": CACHE_KEY_PREFIX,
#             "TIMEOUT": 300,
#         }
#     }
#     CELERY_BROKER_URL = "memory://"
#     CELERY_RESULT_BACKEND = "cache+memory://"


from pathlib import Path

from config.settings.environment import env_bool, env, load_env_file

load_env_file(Path(__file__).resolve().parents[3] / ".env")

from config.settings.base import *  # noqa: E402,F403

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

# ---------- 新增：远程只读数据库配置 ----------
REMOTE_ENABLED = env_bool("REMOTE_AD_DATABASES_ENABLED", False)

if REMOTE_ENABLED:
    # 检查必要的环境变量是否存在
    required_scm = ["SCM_REMOTE_DB_NAME", "SCM_REMOTE_DB_USER", "SCM_REMOTE_DB_PASSWORD",
                    "SCM_REMOTE_DB_HOST", "SCM_REMOTE_DB_PORT"]
    required_ads = ["ADS_ANALYSIS_REMOTE_DB_NAME", "ADS_ANALYSIS_REMOTE_DB_USER",
                    "ADS_ANALYSIS_REMOTE_DB_PASSWORD", "ADS_ANALYSIS_REMOTE_DB_HOST",
                    "ADS_ANALYSIS_REMOTE_DB_PORT"]

    # 如果缺少任一变量，静默跳过（或抛出异常，按需选择）
    if all(env(var) for var in required_scm) and all(env(var) for var in required_ads):
        # SCM 远程库
        DATABASES["scm_remote"] = {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env("SCM_REMOTE_DB_NAME"),
            "USER": env("SCM_REMOTE_DB_USER"),
            "PASSWORD": env("SCM_REMOTE_DB_PASSWORD"),
            "HOST": env("SCM_REMOTE_DB_HOST"),
            "PORT": env("SCM_REMOTE_DB_PORT"),
            "CONN_MAX_AGE": int(env("DB_CONN_MAX_AGE", 0)),
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET SESSION TRANSACTION READ ONLY",
            },
        }
        # ADS Analysis 远程库
        DATABASES["ads_analysis_remote"] = {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env("ADS_ANALYSIS_REMOTE_DB_NAME"),
            "USER": env("ADS_ANALYSIS_REMOTE_DB_USER"),
            "PASSWORD": env("ADS_ANALYSIS_REMOTE_DB_PASSWORD"),
            "HOST": env("ADS_ANALYSIS_REMOTE_DB_HOST"),
            "PORT": env("ADS_ANALYSIS_REMOTE_DB_PORT"),
            "CONN_MAX_AGE": int(env("DB_CONN_MAX_AGE", 0)),
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET SESSION TRANSACTION READ ONLY",
            },
        }
    else:
        # 若变量不全，可选：打印警告或直接忽略
        import warnings
        warnings.warn("远程数据库环境变量缺失，跳过添加 scm_remote / ads_analysis_remote")