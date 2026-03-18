import pytest
from django.utils import timezone

from users.models import GlobalRole, User, UserPreferences, UserSession
from users.services import UserService


@pytest.fixture
def user(db):
    return UserService.register(
        email="alice@example.com",
        password="strongpass123",
        display_name="Alice",
    )


# ---------------------------------------------------------------------------
# Model: User
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserModel:
    def test_create_user_fields(self):
        user = User.objects.create_user(
            email="bob@example.com",
            password="pass",
            display_name="Bob",
        )
        assert user.email == "bob@example.com"
        assert user.display_name == "Bob"
        assert user.global_role == GlobalRole.MEMBER
        assert user.is_active is True
        assert user.timezone == "UTC"

    def test_password_is_hashed(self):
        user = User.objects.create_user(
            email="carol@example.com",
            password="secret",
            display_name="Carol",
        )
        assert user.password != "secret"
        assert user.check_password("secret") is True

    def test_email_is_unique(self):
        User.objects.create_user(email="dup@example.com", password="p", display_name="D1")
        with pytest.raises(Exception):
            User.objects.create_user(email="dup@example.com", password="p", display_name="D2")

    def test_uuid_primary_key(self):
        user = User.objects.create_user(
            email="uuid@example.com", password="p", display_name="U"
        )
        import uuid
        assert isinstance(user.id, uuid.UUID)

    def test_has_elevated_access_for_sa(self):
        user = User.objects.create_user(
            email="sa@example.com", password="p", display_name="SA",
            global_role=GlobalRole.SA,
        )
        assert user.has_elevated_access() is True

    def test_has_elevated_access_for_ga(self):
        user = User.objects.create_user(
            email="ga@example.com", password="p", display_name="GA",
            global_role=GlobalRole.GA,
        )
        assert user.has_elevated_access() is True

    def test_member_has_no_elevated_access(self, user):
        assert user.has_elevated_access() is False

    def test_str(self, user):
        assert str(user) == "alice@example.com"


# ---------------------------------------------------------------------------
# Model: UserSession
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserSession:
    def test_create_session(self, user):
        session = UserSession.objects.create(
            user=user,
            token_hash="abc123",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        assert session.user_id == user.pk
        assert session.is_expired() is False

    def test_expired_session(self, user):
        session = UserSession.objects.create(
            user=user,
            token_hash="old",
            expires_at=timezone.now() - timezone.timedelta(seconds=1),
        )
        assert session.is_expired() is True


# ---------------------------------------------------------------------------
# Model: UserPreferences
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserPreferences:
    def test_preferences_created_with_user(self, user):
        assert UserPreferences.objects.filter(user=user).exists()

    def test_default_values(self, user):
        prefs = user.preferences
        assert prefs.theme == UserPreferences.Theme.SYSTEM
        assert prefs.language == "en"
        assert prefs.digest_frequency == UserPreferences.DigestFrequency.REALTIME
        assert prefs.default_view == UserPreferences.DefaultView.LIST

    def test_notification_channels_set_on_register(self, user):
        assert user.preferences.notification_channels["email"] is True


# ---------------------------------------------------------------------------
# Service: UserService
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserService:
    def test_register_creates_user(self):
        user = UserService.register(
            email="new@example.com", password="pass", display_name="New"
        )
        assert User.objects.filter(email="new@example.com").exists()
        assert user.pk is not None

    def test_register_creates_preferences(self):
        user = UserService.register(
            email="pref@example.com", password="pass", display_name="Pref"
        )
        assert hasattr(user, "preferences")

    def test_register_duplicate_email_raises(self, user):
        with pytest.raises(ValueError, match="already exists"):
            UserService.register(
                email="alice@example.com", password="pass", display_name="Alice2"
            )

    def test_deactivate_user(self, user):
        UserService.deactivate(user)
        user.refresh_from_db()
        assert user.is_active is False

    def test_deactivate_removes_sessions(self, user):
        UserSession.objects.create(
            user=user,
            token_hash="tok",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        UserService.deactivate(user)
        assert user.sessions.count() == 0

    def test_change_global_role(self, user):
        UserService.change_global_role(user, GlobalRole.GA)
        user.refresh_from_db()
        assert user.global_role == GlobalRole.GA

    def test_change_global_role_invalid_raises(self, user):
        with pytest.raises(ValueError, match="Invalid role"):
            UserService.change_global_role(user, "SUPERUSER")

    def test_record_login_sets_last_login(self, user):
        UserService.record_login(user)
        user.refresh_from_db()
        assert user.last_login is not None

    def test_create_and_invalidate_session(self, user):
        session = UserService.create_session(
            user=user,
            token_hash="mytoken",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        assert UserSession.objects.filter(token_hash="mytoken").exists()
        UserService.invalidate_session("mytoken")
        assert not UserSession.objects.filter(token_hash="mytoken").exists()

    def test_cleanup_expired_sessions(self, user):
        UserSession.objects.create(
            user=user, token_hash="expired",
            expires_at=timezone.now() - timezone.timedelta(hours=1),
        )
        UserSession.objects.create(
            user=user, token_hash="valid",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        deleted = UserService.cleanup_expired_sessions()
        assert deleted == 1
        assert UserSession.objects.filter(token_hash="valid").exists()
