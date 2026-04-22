import logging

from django.conf import settings
from django.core.mail import send_mail

from dodoist.celery import app

logger = logging.getLogger("dodoist")


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=5,
    default_retry_delay=60,
)
def send_email_notification(self, notification_id: str) -> None:
    from users.models import Notification, UserPreferences
    try:
        notif = Notification.objects.select_related("recipient", "actor").get(pk=notification_id)
    except Notification.DoesNotExist:
        return

    try:
        prefs = notif.recipient.preferences
        if not prefs.notification_channels.get("email"):
            return
    except UserPreferences.DoesNotExist:
        return

    actor_name = notif.actor.display_name if notif.actor else "Dodoist"
    subject = f"[Dodoist] {actor_name}: {notif.message[:80]}"
    body = (
        f"Hi {notif.recipient.display_name},\n\n"
        f"{notif.message}\n\n"
        f"Open the app: {settings.FRONTEND_BASE_URL}\n\n"
        f"— The Dodoist team"
    )

    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[notif.recipient.email],
        fail_silently=False,
    )
    logger.info("Email notification sent for notification %s", notification_id)


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=5,
    default_retry_delay=60,
)
def send_verification_email(self, user_id: str, token: str) -> None:
    from users.models import User
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return
    link = f"{settings.FRONTEND_BASE_URL}/verify-email?token={token}"
    send_mail(
        subject="Verify your Dodoist email",
        message=(
            f"Hi {user.display_name},\n\n"
            f"Verify your email by clicking this link:\n{link}\n\n"
            f"This link expires in 24 hours.\n\n"
            f"— The Dodoist team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=5,
    default_retry_delay=60,
)
def send_workspace_invite_email(self, invite_id: str, raw_token: str) -> None:
    from projects.models import WorkspaceInvitation
    try:
        invite = WorkspaceInvitation.objects.select_related(
            "workspace", "invited_by"
        ).get(pk=invite_id)
    except WorkspaceInvitation.DoesNotExist:
        return
    inviter = invite.invited_by.display_name if invite.invited_by else "Someone"
    link = f"{settings.FRONTEND_BASE_URL}/invites/{raw_token}"
    send_mail(
        subject=f"[Dodoist] You've been invited to '{invite.workspace.name}'",
        message=(
            f"Hi,\n\n"
            f"{inviter} has invited you to join the workspace '{invite.workspace.name}' on Dodoist "
            f"as {invite.role_to_grant.capitalize()}.\n\n"
            f"Accept the invitation:\n{link}\n\n"
            f"This link expires in 7 days.\n\n"
            f"— The Dodoist team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invite.email],
        fail_silently=False,
    )
    logger.info("Workspace invite email sent for invite %s", invite_id)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_workspace_invite_email(self, invite_id: str, raw_token: str) -> None:
    from projects.models import WorkspaceInvitation
    try:
        invite = WorkspaceInvitation.objects.select_related("workspace", "invited_by").get(pk=invite_id)
    except WorkspaceInvitation.DoesNotExist:
        return
    link = f"{settings.FRONTEND_BASE_URL}/invites/{raw_token}"
    inviter_name = invite.invited_by.display_name if invite.invited_by else "Someone"
    role_label = invite.role_to_grant.capitalize()
    try:
        send_mail(
            subject=f"You're invited to join '{invite.workspace.name}' on Dodoist",
            message=(
                f"Hi,\n\n"
                f"{inviter_name} invited you to join '{invite.workspace.name}' as {role_label}.\n\n"
                f"Accept the invitation:\n{link}\n\n"
                f"This link expires in 7 days."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invite.email],
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
    send_mail(
        subject="Reset your Dodoist password",
        message=(
            f"Hi {user.display_name},\n\n"
            f"Reset your password by clicking this link:\n{link}\n\n"
            f"This link expires in 1 hour. If you didn't request this, you can ignore this email.\n\n"
            f"— The Dodoist team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
