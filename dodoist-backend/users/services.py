import hashlib
import secrets
import uuid

from django.db import transaction
from django.utils import timezone

from .models import GlobalRole, Notification, NotificationType, User, UserPreferences, UserSession


def _extract_mention_ids(node: dict, ids: set) -> None:
    """Recursively collect user UUIDs from ProseMirror mention nodes."""
    if node.get("type") == "mention":
        raw = node.get("attrs", {}).get("id")
        if raw:
            try:
                ids.add(uuid.UUID(str(raw)))
            except (ValueError, AttributeError):
                pass
    for child in node.get("content", []):
        _extract_mention_ids(child, ids)


class NotificationService:
    @staticmethod
    def create(
        recipient: User,
        notification_type: str,
        message: str,
        actor: User | None = None,
        task_id=None,
        project_id=None,
    ) -> Notification:
        notif = Notification.objects.create(
            recipient=recipient,
            actor=actor,
            type=notification_type,
            message=message,
            task_id=task_id,
            project_id=project_id,
        )
        user_id = str(recipient.pk)
        notif_pk = str(notif.pk)

        def _on_commit():
            # Push real-time SSE event to all open connections for this user.
            from realtime.channels import publish
            publish(user_id, {"type": "notification", "id": notif_pk})

            # Email delivery via Celery (respects email channel preference).
            try:
                prefs = recipient.preferences
                if prefs.notification_channels.get("email"):
                    from users.tasks import send_email_notification
                    send_email_notification.delay(notif_pk)
            except UserPreferences.DoesNotExist:
                pass

        transaction.on_commit(_on_commit)
        return notif

    @staticmethod
    def notify_watchers(
        task,
        notification_type: str,
        message: str,
        actor: User,
    ) -> None:
        """Notify the task creator and all assignees, excluding the actor."""
        recipients: set[User] = set()
        if task.created_by_id:
            recipients.add(task.created_by)
        if task.assigned_to_id:
            recipients.add(task.assigned_to)
        for assignment in task.co_assignments.select_related("user").all():
            recipients.add(assignment.user)
        recipients.discard(actor)

        for recipient in recipients:
            NotificationService.create(
                recipient=recipient,
                notification_type=notification_type,
                message=message,
                actor=actor,
                task_id=task.pk,
                project_id=task.project_id,
            )

    @staticmethod
    def create_for_mentions(body_json: dict, actor: User, task) -> None:
        """Parse a ProseMirror body and create 'mentioned' notifications."""
        if not body_json or not isinstance(body_json, dict):
            return
        mention_ids: set[uuid.UUID] = set()
        _extract_mention_ids(body_json, mention_ids)
        for user_id in mention_ids:
            try:
                recipient = User.objects.get(pk=user_id, is_active=True)
            except User.DoesNotExist:
                continue
            if recipient.pk == actor.pk:
                continue
            NotificationService.create(
                recipient=recipient,
                notification_type=NotificationType.MENTIONED,
                message=f"{actor.display_name} mentioned you in a comment on '{task.title}'",
                actor=actor,
                task_id=task.pk,
                project_id=task.project_id,
            )


class UserService:
    @staticmethod
    @transaction.atomic
    def register(
        email: str,
        password: str,
        display_name: str,
        user_timezone: str = "UTC",
        invite_token: str | None = None,
    ) -> User:
        if User.objects.filter(email=email).exists():
            raise ValueError(f"User with email '{email}' already exists.")

        user = User.objects.create_user(
            email=email,
            password=password,
            display_name=display_name,
            timezone=user_timezone,
        )
        UserPreferences.objects.create(
            user=user,
            notification_channels={"email": True, "push": False, "in_app": True},
        )

        from projects.services import WorkspaceService  # deferred to avoid circular import
        WorkspaceService.create_personal_workspace(user)

        if invite_token:
            try:
                from projects.invitations import InvitationService
                InvitationService.accept(invite_token, user)
            except Exception:
                pass  # don't block signup if invite is invalid/expired

        return user

    @staticmethod
    def set_active_workspace(user: User, workspace) -> User:
        from projects.models import WorkspaceMember
        if not user.has_elevated_access():
            is_member = WorkspaceMember.objects.filter(workspace=workspace, user=user).exists()
            if not is_member:
                raise ValueError("User is not a member of this workspace.")
        user.active_workspace = workspace
        user.save(update_fields=["active_workspace"])
        return user

    @staticmethod
    def deactivate(user: User) -> User:
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        user.sessions.all().delete()
        return user

    @staticmethod
    def change_global_role(user: User, new_role: str) -> User:
        if new_role not in GlobalRole.values:
            raise ValueError(f"Invalid role: '{new_role}'. Choices: {GlobalRole.values}")
        user.global_role = new_role
        user.save(update_fields=["global_role", "updated_at"])
        return user

    @staticmethod
    def record_login(user: User) -> None:
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

    @staticmethod
    def create_session(
        user: User,
        token_hash: str,
        expires_at,
        refresh_token_hash: str,
        refresh_expires_at,
        device_info: str = "",
        ip_address: str | None = None,
    ) -> UserSession:
        return UserSession.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=expires_at,
            refresh_token_hash=refresh_token_hash,
            refresh_expires_at=refresh_expires_at,
            device_info=device_info,
            ip_address=ip_address,
        )

    @staticmethod
    def rotate_access_token(session: UserSession, new_token_hash: str, new_expires_at) -> None:
        session.token_hash = new_token_hash
        session.expires_at = new_expires_at
        session.save(update_fields=["token_hash", "expires_at"])

    @staticmethod
    def invalidate_session(token_hash: str) -> None:
        UserSession.objects.filter(token_hash=token_hash).delete()

    @staticmethod
    def invalidate_session_by_refresh(refresh_token_hash: str) -> None:
        UserSession.objects.filter(refresh_token_hash=refresh_token_hash).delete()

    @staticmethod
    def cleanup_expired_sessions() -> int:
        deleted, _ = UserSession.objects.filter(expires_at__lt=timezone.now()).delete()
        return deleted

    # ── Email verification ────────────────────────────────────────────────────

    @staticmethod
    def send_verification_email(user: User) -> None:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        user.verification_token_hash = token_hash
        user.verification_token_expires_at = timezone.now() + timezone.timedelta(hours=24)
        user.save(update_fields=["verification_token_hash", "verification_token_expires_at"])
        from users.tasks import send_verification_email as task
        task.delay(str(user.pk), token)

    @staticmethod
    def verify_email(token: str) -> User:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            user = User.objects.get(verification_token_hash=token_hash, is_active=True)
        except User.DoesNotExist:
            raise ValueError("Invalid or expired verification token.")
        if (
            user.verification_token_expires_at
            and timezone.now() > user.verification_token_expires_at
        ):
            raise ValueError("Verification token has expired. Please request a new one.")
        user.email_verified = True
        user.verification_token_hash = ""
        user.verification_token_expires_at = None
        user.save(update_fields=[
            "email_verified", "verification_token_hash",
            "verification_token_expires_at", "updated_at",
        ])
        return user

    # ── Password reset ────────────────────────────────────────────────────────

    @staticmethod
    def send_password_reset_email(email: str) -> None:
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return  # silent — don't reveal whether email exists
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        user.password_reset_token_hash = token_hash
        user.password_reset_expires_at = timezone.now() + timezone.timedelta(hours=1)
        user.save(update_fields=["password_reset_token_hash", "password_reset_expires_at"])
        from users.tasks import send_password_reset_email as task
        task.delay(str(user.pk), token)

    @staticmethod
    @transaction.atomic
    def reset_password(token: str, new_password: str) -> User:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            user = User.objects.get(password_reset_token_hash=token_hash, is_active=True)
        except User.DoesNotExist:
            raise ValueError("Invalid or expired reset token.")
        if not user.password_reset_expires_at or timezone.now() > user.password_reset_expires_at:
            raise ValueError("Reset token has expired.")
        user.set_password(new_password)
        user.password_reset_token_hash = ""
        user.password_reset_expires_at = None
        user.save(update_fields=[
            "password", "password_reset_token_hash", "password_reset_expires_at", "updated_at"
        ])
        user.sessions.all().delete()
        return user
