import uuid

from django.contrib.auth.models import AbstractBaseUser
from django.db import models
from django.utils import timezone as tz

from .managers import UserManager


class GlobalRole(models.TextChoices):
    SA = "SA", "System Admin"
    GA = "GA", "Global Admin"
    MEMBER = "member", "Member"


class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=255)
    avatar_url = models.CharField(max_length=2048, blank=True, default="")
    timezone = models.CharField(max_length=64, default="UTC")
    global_role = models.CharField(
        max_length=10, choices=GlobalRole.choices, default=GlobalRole.MEMBER
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=tz.now)
    updated_at = models.DateTimeField(auto_now=True)
    # last_login is inherited from AbstractBaseUser (maps to last_login_at in schema)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]

    objects = UserManager()

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email

    def has_elevated_access(self) -> bool:
        return self.global_role in (GlobalRole.SA, GlobalRole.GA)


class UserSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    token_hash = models.CharField(max_length=255)
    device_info = models.CharField(max_length=512, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(default=tz.now)

    class Meta:
        db_table = "user_sessions"

    def __str__(self):
        return f"Session({self.user_id}, expires={self.expires_at})"

    def is_expired(self) -> bool:
        return tz.now() >= self.expires_at


class UserPreferences(models.Model):
    class Theme(models.TextChoices):
        LIGHT = "light", "Light"
        DARK = "dark", "Dark"
        SYSTEM = "system", "System"

    class DigestFrequency(models.TextChoices):
        REALTIME = "realtime", "Realtime"
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"

    class DefaultView(models.TextChoices):
        LIST = "list", "List"
        BOARD = "board", "Board"
        CALENDAR = "calendar", "Calendar"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preferences")
    theme = models.CharField(max_length=10, choices=Theme.choices, default=Theme.SYSTEM)
    language = models.CharField(max_length=10, default="en")
    notification_channels = models.JSONField(
        default=dict,
        help_text='e.g. {"email": true, "push": false, "in_app": true}',
    )
    digest_frequency = models.CharField(
        max_length=10, choices=DigestFrequency.choices, default=DigestFrequency.REALTIME
    )
    default_view = models.CharField(
        max_length=10, choices=DefaultView.choices, default=DefaultView.LIST
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_preferences"

    def __str__(self):
        return f"Preferences({self.user_id})"
