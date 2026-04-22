from django.utils import timezone

from dodoist.celery import app


@app.task
def purge_expired_workspaces() -> int:
    from .models import Workspace
    expired = Workspace.objects.filter(
        delete_scheduled_for__lte=timezone.now(),
        deleted_at__isnull=False,
    )
    count = expired.count()
    expired.delete()
    return count
