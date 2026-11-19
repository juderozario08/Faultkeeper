"""Settings for the test suite: no external services required."""

import os

os.environ.setdefault("DJANGO_DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")

from .settings import *  # noqa: E402,F403

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
CELERY_TASK_ALWAYS_EAGER = True
MIDDLEWARE = [m for m in MIDDLEWARE if not m.startswith("whitenoise")]  # noqa: F405
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
