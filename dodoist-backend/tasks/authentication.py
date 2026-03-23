import hashlib

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from users.models import UserSession


class SessionTokenAuthentication(BaseAuthentication):
    """
    Authenticates requests using a bearer token stored in UserSession.

    The client must send:
        Authorization: Bearer <raw_token>

    The raw token is hashed with SHA-256 before lookup. Sessions must be
    created via UserService.create_session() with a SHA-256 hash of the token.
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
