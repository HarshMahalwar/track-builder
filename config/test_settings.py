"""
Test settings for track-builder.
Uses SQLite without GIS for testing.
"""

from .settings import *  # noqa: F401, F403

# Override database for testing - use SQLite without GIS
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Ensure GIS is disabled for tests
USE_GIS = False

# Disable Celery task execution during tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use faster password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable CORS during tests
CORS_ALLOW_ALL_ORIGINS = True

# Use in-memory cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
