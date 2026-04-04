import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import AuthUserSerializer, LoginSerializer, RegisterSerializer
from .services import UserService


SESSION_DURATION_DAYS = 30


class RegisterView(APIView):
    """
    POST /api/auth/register

    Creates a new user account and returns a session token.
    The token is valid for 30 days. No authentication required.
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

        raw_token, _session = _create_session_for_user(user, request)
        UserService.record_login(user)

        return Response(
            {
                "token": raw_token,
                "user": AuthUserSerializer(user).data,
            },
            status=201,
        )


class LoginView(APIView):
    """
    POST /api/auth/login

    Validates credentials and returns a session token.
    The token is valid for 30 days. No authentication required.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # authenticate() uses USERNAME_FIELD ("email") when passed as "username"
        user = authenticate(request, username=data["email"], password=data["password"])
        if user is None:
            return Response({"detail": "Invalid email or password."}, status=401)

        if not user.is_active:
            return Response({"detail": "This account has been deactivated."}, status=403)

        raw_token, _session = _create_session_for_user(user, request)
        UserService.record_login(user)

        return Response(
            {
                "token": raw_token,
                "user": AuthUserSerializer(user).data,
            },
            status=200,
        )


class LogoutView(APIView):
    """
    POST /api/auth/logout

    Invalidates the current session. Requires authentication.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # request.auth is the UserSession object returned by SessionTokenAuthentication
        session = request.auth
        UserService.invalidate_session(session.token_hash)
        return Response(status=204)


class MeView(APIView):
    """
    GET /api/users/me

    Returns the authenticated user's profile.
    """

    def get(self, request):
        user = request.user
        return Response({
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "timezone": user.timezone,
        })


def _create_session_for_user(user, request):
    """
    Generates a raw bearer token, stores its SHA-256 hash in a new UserSession,
    and returns the (raw_token, session) tuple.

    The raw token is sent to the client; only the hash is persisted.
    """
    raw_token = secrets.token_hex(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = timezone.now() + timedelta(days=SESSION_DURATION_DAYS)

    session = UserService.create_session(
        user=user,
        token_hash=token_hash,
        expires_at=expires_at,
        device_info=request.META.get("HTTP_USER_AGENT", "")[:512],
        ip_address=_get_client_ip(request),
    )
    return raw_token, session


def _get_client_ip(request):
    """Returns the client IP address, respecting the X-Forwarded-For header."""
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
