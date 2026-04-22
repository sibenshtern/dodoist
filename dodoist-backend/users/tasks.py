import logging

from dodoist.celery import app

logger = logging.getLogger("dodoist")


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_notification(self, notification_id: str) -> None:
    """
    Send an email for a Notification row.
    Phase 4 will wire an actual SMTP backend; this stub logs and returns.
    """
    logger.info("send_email_notification queued for notification %s (email backend pending Phase 4)", notification_id)
