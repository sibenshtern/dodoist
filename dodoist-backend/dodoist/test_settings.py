"""
Test settings — inherits from the main settings but forces DEBUG=True and a
deterministic SECRET_KEY so the fail-fast checks don't block the test runner.
"""
import os

os.environ.setdefault("DJANGO_DEBUG", "true")

from dodoist.settings import *  # noqa: F401, F403, E402

DEBUG = True
SECRET_KEY = "test-only-insecure-key-not-for-production"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
# Use in-memory broker for tests
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
