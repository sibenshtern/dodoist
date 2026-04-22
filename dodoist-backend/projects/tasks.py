import logging

from django.utils import timezone

from dodoist.celery import app

logger = logging.getLogger("dodoist")


@app.task
def purge_expired_workspaces() -> int:
    from projects.models import Workspace
    qs = Workspace.objects.filter(
        deleted_at__isnull=False,
        delete_scheduled_for__lte=timezone.now(),
    )
    count, _ = qs.delete()
    if count:
        logger.info("Purged %d expired workspace(s)", count)
    return count
