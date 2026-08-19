"""
Django settings for track-builder project.

Supports two modes:
- Development: SQLite with standard Django models
- Production: PostgreSQL/PostGIS with GIS models
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Load .env file
# ---------------------------------------------------------------------------

def load_env_file():
    """Load environment variables from .env file."""
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env_file()

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-6rq85ergv9y^*=m%n46uk(^jf#guquo+pu^es*f-+&oyb&))cy",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS: list[str] = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",") + [
    ".ngrok-free.app",
    ".ngrok-free.dev",
]

# ---------------------------------------------------------------------------
# GIS Detection
# ---------------------------------------------------------------------------

# Enable GIS if DATABASE_ENGINE is set to postgis or USE_GIS is explicitly set
USE_GIS = os.environ.get("USE_GIS", "false").lower() in ("true", "1", "yes")
DB_ENGINE = os.environ.get("DB_ENGINE", "django.db.backends.sqlite3")

if DB_ENGINE == "django.contrib.gis.db.backends.postgis" or USE_GIS:
    DATABASE_BACKEND = "django.contrib.gis.db.backends.postgis"
    USE_GIS = True
else:
    DATABASE_BACKEND = DB_ENGINE

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third-party
    "rest_framework",
    "django_filters",
    "corsheaders",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    # Local
    "accounts.apps.AccountsConfig",
    "tracks.apps.TracksConfig",
    "api.apps.ApiConfig",
]

if USE_GIS:
    INSTALLED_APPS.insert(0, "django.contrib.gis")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": DATABASE_BACKEND,
        "NAME": os.environ.get("DB_NAME", str(BASE_DIR / "db.sqlite3")),
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", ""),
        "PORT": os.environ.get("DB_PORT", ""),
    }
}

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.User"

# ---------------------------------------------------------------------------
# django-allauth
# ---------------------------------------------------------------------------

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_ON_GET = True

# Google OAuth provider
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = (
    os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    if os.environ.get("CORS_ALLOWED_ORIGINS")
    else []
)
CORS_ALLOW_ALL_ORIGINS = DEBUG

# CSRF trusted origins for ngrok
CSRF_TRUSTED_ORIGINS = [
    "https://linked-untracked-sprawl.ngrok-free.dev",
    "https://linked-untracked-sprawl.ngrok-free.app",
]

# Trust ngrok's X-Forwarded-Proto header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "tracks": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
