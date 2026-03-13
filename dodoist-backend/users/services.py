from django.db import transaction
from django.utils import timezone

from .models import GlobalRole, User, UserPreferences, UserSession


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
        device_info: str = "",
        ip_address: str | None = None,
    ) -> UserSession:
        return UserSession.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=expires_at,
            device_info=device_info,
            ip_address=ip_address,
        )

    @staticmethod
    def invalidate_session(token_hash: str) -> None:
        UserSession.objects.filter(token_hash=token_hash).delete()

    @staticmethod
    def cleanup_expired_sessions() -> int:
        deleted, _ = UserSession.objects.filter(expires_at__lt=timezone.now()).delete()
        return deleted
