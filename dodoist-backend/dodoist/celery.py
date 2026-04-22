import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dodoist.settings")

app = Celery("dodoist")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
