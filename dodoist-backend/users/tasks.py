import logging

from django.conf import settings
from django.core.mail import send_mail

from dodoist.celery import app

logger = logging.getLogger("dodoist")


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_notification(self, notification_id: str) -> None:
    logger.info("send_email_notification queued for notification %s", notification_id)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email(self, user_id: str, token: str) -> None:
    from users.models import User
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return
    link = f"{settings.FRONTEND_BASE_URL}/verify-email?token={token}"
    try:
        send_mail(
            subject="Verify your Dodoist email",
            message=f"Hi {user.display_name},\n\nVerify your email:\n{link}\n\nThis link expires in 24 hours.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email(self, user_id: str, token: str) -> None:
    from users.models import User
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return
    link = f"{settings.FRONTEND_BASE_URL}/reset-password?token={token}"
    try:
        send_mail(
            subject="Reset your Dodoist password",
            message=f"Hi {user.display_name},\n\nReset your password:\n{link}\n\nThis link expires in 1 hour.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as exc:
        raise self.retry(exc=exc)
