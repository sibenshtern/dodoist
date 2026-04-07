import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth import authenticate
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import GlobalRole, User, UserPreferences, UserSession
from .serializers import (
    AuthUserSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserListSerializer,
    UserPreferencesSerializer,
    UserPreferencesUpdateSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
)
from .services import UserService


ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 7
REFRESH_COOKIE_NAME = "refresh_token"


class RegisterView(APIView):
    """
    POST /api/auth/register

    Creates a new user account. Returns a 15-minute access token in the body
    and sets a 7-day HttpOnly refresh token cookie.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            user = UserService.register(
                email=data["email"],
                password=data["password"],
                display_name=data["display_name"],
                user_timezone=data.get("timezone", "UTC"),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        access_token, raw_refresh, _session = _create_session_for_user(user, request)
        UserService.record_login(user)

        response = Response(
            {
                "access_token": access_token,
                "expires_in": ACCESS_TOKEN_MINUTES * 60,
                "user": AuthUserSerializer(user).data,
            },
            status=201,
        )
        _set_refresh_cookie(response, raw_refresh)
        return response


class LoginView(APIView):
    """
    POST /api/auth/login

    Validates credentials. Returns a 15-minute access token in the body
    and sets a 7-day HttpOnly refresh token cookie.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = authenticate(request, username=data["email"], password=data["password"])
        if user is None:
            return Response({"detail": "Invalid email or password."}, status=401)

        if not user.is_active:
            return Response({"detail": "This account has been deactivated."}, status=403)

        access_token, raw_refresh, _session = _create_session_for_user(user, request)
        UserService.record_login(user)

        response = Response(
            {
                "access_token": access_token,
                "expires_in": ACCESS_TOKEN_MINUTES * 60,
                "user": AuthUserSerializer(user).data,
            },
            status=200,
        )
        _set_refresh_cookie(response, raw_refresh)
        return response


class RefreshView(APIView):
    """
    POST /api/auth/refresh

    Exchanges the HttpOnly refresh token cookie for a new short-lived access token.
    No Authorization header required.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not raw_refresh:
            return Response({"detail": "No refresh token."}, status=401)

        refresh_hash = hashlib.sha256(raw_refresh.encode()).hexdigest()
        try:
            session = (
                UserSession.objects
                .select_related("user")
                .get(refresh_token_hash=refresh_hash)
            )
        except UserSession.DoesNotExist:
            return Response({"detail": "Invalid refresh token."}, status=401)

        if session.is_refresh_expired():
            session.delete()
            return Response({"detail": "Refresh token expired. Please log in again."}, status=401)

        if not session.user.is_active:
            return Response({"detail": "User account is disabled."}, status=403)

        # Issue a new access token
        new_raw_access = secrets.token_hex(32)
        new_access_hash = hashlib.sha256(new_raw_access.encode()).hexdigest()
        new_expires_at = timezone.now() + timedelta(minutes=ACCESS_TOKEN_MINUTES)
        UserService.rotate_access_token(session, new_access_hash, new_expires_at)

        return Response(
            {
                "access_token": new_raw_access,
                "expires_in": ACCESS_TOKEN_MINUTES * 60,
            },
            status=200,
        )


class LogoutView(APIView):
    """
    POST /api/auth/logout

    Invalidates the current session. Requires authentication.
    Clears the refresh token cookie.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session = request.auth
        session.delete()
        response = Response(status=204)
        response.delete_cookie(REFRESH_COOKIE_NAME, samesite="Strict")
        return response


class MeView(APIView):
    """
    GET /api/users/me

    Returns the authenticated user's profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserProfileSerializer(request.user).data)


class UserListView(APIView):
    """
    GET /api/users/  — list all users (SA/GA only)
    """
    def get(self, request):
        if not request.user.has_elevated_access():
            return Response({"detail": "Forbidden."}, status=403)
        qs = User.objects.all().order_by("created_at")
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(
                models.Q(display_name__icontains=search) | models.Q(email__icontains=search)
            )
        is_active = request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return Response(UserListSerializer(qs, many=True).data)


class UserDetailView(APIView):
    """
    GET    /api/users/<pk>/  — retrieve a user
    PATCH  /api/users/<pk>/  — update profile (own account or SA)
    DELETE /api/users/<pk>/  — deactivate user (SA only)
    """
    def _get_user_or_404(self, pk):
        return get_object_or_404(User, pk=pk)

    def get(self, request, pk):
        user = self._get_user_or_404(pk)
        # SA/GA can view anyone; regular users can view workspace members (simplified: allow all authenticated)
        return Response(UserListSerializer(user).data)

    def patch(self, request, pk):
        target = self._get_user_or_404(pk)
        is_own = target.pk == request.user.pk
        is_sa = request.user.global_role == GlobalRole.SA

        if not is_own and not is_sa:
            return Response({"detail": "You may only edit your own profile."}, status=403)

        # Only SA may change global_role
        if "global_role" in request.data and not is_sa:
            return Response({"detail": "Only SA may change global_role."}, status=403)

        serializer = UserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Password change via headers
        current_password = request.META.get("HTTP_X_CURRENT_PASSWORD")
        new_password = request.META.get("HTTP_X_NEW_PASSWORD")
        if new_password:
            if not is_sa and not current_password:
                return Response({"detail": "X-Current-Password header required."}, status=400)
            if not is_sa and not target.check_password(current_password):
                return Response({"detail": "Current password is incorrect."}, status=400)
            if len(new_password) < 8:
                return Response({"detail": "New password must be at least 8 characters."}, status=422)
            target.set_password(new_password)

        for field, value in data.items():
            setattr(target, field, value)
        target.save()
        return Response(UserListSerializer(target).data)

    def delete(self, request, pk):
        if request.user.global_role != GlobalRole.SA:
            return Response({"detail": "Only SA may deactivate users."}, status=403)
        target = self._get_user_or_404(pk)
        target.is_active = False
        target.save(update_fields=["is_active"])
        return Response(status=204)


class UserPreferencesView(APIView):
    """
    GET /api/users/<pk>/preferences/  — retrieve preferences
    PUT /api/users/<pk>/preferences/  — replace preferences
    """
    def _check_access(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        is_own = target.pk == request.user.pk
        is_sa = request.user.global_role == GlobalRole.SA
        if not is_own and not is_sa:
            return None, Response({"detail": "Forbidden."}, status=403)
        return target, None

    def get(self, request, pk):
        target, err = self._check_access(request, pk)
        if err:
            return err
        prefs = get_object_or_404(UserPreferences, user=target)
        return Response(UserPreferencesSerializer(prefs).data)

    def put(self, request, pk):
        target, err = self._check_access(request, pk)
        if err:
            return err
        serializer = UserPreferencesUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        prefs = get_object_or_404(UserPreferences, user=target)
        # PUT = full replace: set defaults for omitted fields
        prefs.theme = data.get("theme", "system")
        prefs.language = data.get("language", "en")
        prefs.notification_channels = data.get("notification_channels", {})
        prefs.digest_frequency = data.get("digest_frequency", "realtime")
        prefs.default_view = data.get("default_view", "list")
        prefs.save()
        return Response(UserPreferencesSerializer(prefs).data)


def _create_session_for_user(user, request):
    """
    Generates a short-lived access token (15 min) and a long-lived refresh token (7 days).
    Only hashes are persisted in the DB. Returns (raw_access, raw_refresh, session).
    """
    raw_access = secrets.token_hex(32)
    access_hash = hashlib.sha256(raw_access.encode()).hexdigest()
    access_expires = timezone.now() + timedelta(minutes=ACCESS_TOKEN_MINUTES)

    raw_refresh = secrets.token_hex(32)
    refresh_hash = hashlib.sha256(raw_refresh.encode()).hexdigest()
    refresh_expires = timezone.now() + timedelta(days=REFRESH_TOKEN_DAYS)

    session = UserService.create_session(
        user=user,
        token_hash=access_hash,
        expires_at=access_expires,
        refresh_token_hash=refresh_hash,
        refresh_expires_at=refresh_expires,
        device_info=request.META.get("HTTP_USER_AGENT", "")[:512],
        ip_address=_get_client_ip(request),
    )
    return raw_access, raw_refresh, session


def _set_refresh_cookie(response, raw_refresh: str) -> None:
    """Sets the HttpOnly refresh token cookie on a response."""
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        raw_refresh,
        max_age=REFRESH_TOKEN_DAYS * 86400,
        httponly=True,
        secure=False,   # Set to True in production (requires HTTPS)
        samesite="Lax", # Lax allows the cookie to be sent on top-level navigations (e.g., redirects)
        path="/api/auth/",
    )


def _get_client_ip(request):
    """Returns the client IP address, respecting the X-Forwarded-For header."""
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class NotificationListView(APIView):
    """
    GET /api/notifications/  — list notifications for current user
    """
    def get(self, request):
        from users.models import Notification
        qs = Notification.objects.filter(recipient=request.user).order_by("-created_at")
        is_read = request.query_params.get("is_read")
        if is_read is not None:
            qs = qs.filter(is_read=is_read.lower() == "true")
        ntype = request.query_params.get("type")
        if ntype:
            qs = qs.filter(type=ntype)
        limit = min(int(request.query_params.get("limit", 50)), 100)
        data = [
            {
                "id": str(n.id),
                "type": n.type,
                "message": n.message,
                "task_id": str(n.task_id) if n.task_id else None,
                "project_id": str(n.project_id) if n.project_id else None,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
                "read_at": n.read_at.isoformat() if n.read_at else None,
            }
            for n in qs[:limit]
        ]
        return Response(data)


class NotificationDetailView(APIView):
    """
    PATCH  /api/notifications/<pk>/  — mark as read
    DELETE /api/notifications/<pk>/  — delete notification
    """
    def _get_notif(self, request, pk):
        from users.models import Notification
        return get_object_or_404(Notification, pk=pk, recipient=request.user)

    def patch(self, request, pk):
        from django.utils import timezone as tz
        n = self._get_notif(request, pk)
        is_read = request.data.get("is_read")
        if is_read is True or is_read == "true":
            n.is_read = True
            n.read_at = tz.now()
            n.save(update_fields=["is_read", "read_at"])
        return Response({"id": str(n.id), "is_read": n.is_read})

    def delete(self, request, pk):
        n = self._get_notif(request, pk)
        n.delete()
        return Response(status=204)


class NotificationReadAllView(APIView):
    """POST /api/notifications/read-all/"""
    def post(self, request):
        from users.models import Notification
        from django.utils import timezone as tz
        now = tz.now()
        count = Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True, read_at=now
        )
        return Response({"marked_count": count})
