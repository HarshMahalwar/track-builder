"""
Pytest configuration for track-builder.
"""

import os

import django
from django.conf import settings


def pytest_configure(config):
    """Configure Django settings for pytest."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.test_settings")
    django.setup()
