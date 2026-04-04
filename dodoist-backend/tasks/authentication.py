import hashlib

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from users.models import UserSession


class SessionTokenAuthentication(BaseAuthentication):
    """
    Authenticates requests using a short-lived access token (15-minute TTL).

    The client must send:
        Authorization: Bearer <raw_access_token>

    The raw token is hashed with SHA-256 before lookup against UserSession.token_hash.
    When the access token expires, the client must call POST /api/auth/refresh using
    the HttpOnly refresh token cookie to obtain a new access token.
    """

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return None  # Not our auth scheme; let other authenticators try

        raw_token = auth_header[len("Bearer "):]
        if not raw_token:
            return None

        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        try:
            session = (
                UserSession.objects
                .select_related("user")
                .get(token_hash=token_hash)
            )
        except UserSession.DoesNotExist:
            raise AuthenticationFailed("Invalid or expired token.")

        if session.is_expired():
            raise AuthenticationFailed("Token has expired.")

        if not session.user.is_active:
            raise AuthenticationFailed("User account is disabled.")

        return (session.user, session)

    def authenticate_header(self, request):
        return "Bearer"
