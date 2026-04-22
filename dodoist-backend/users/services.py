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
        try:
            prefs = recipient.preferences
            if prefs.notification_channels.get("email"):
                from users.tasks import send_email_notification
                send_email_notification.delay(str(notif.pk))
        except UserPreferences.DoesNotExist:
            pass
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
    def register(email: str, password: str, display_name: str, user_timezone: str = "UTC") -> User:
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
