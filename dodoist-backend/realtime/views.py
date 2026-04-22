import hashlib
import json
import queue
import secrets

from django.core.cache import cache
from django.http import StreamingHttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from tasks.authentication import SessionTokenAuthentication

from . import channels


# ---------------------------------------------------------------------------
# SSE token issuance
# ---------------------------------------------------------------------------

class SSETokenView(APIView):
    """
    POST /api/auth/sse-token/
    Returns a 60-second single-use token the client passes as ?token= to /api/events/.
    """
    authentication_classes = [SessionTokenAuthentication]

    def post(self, request):
        token = secrets.token_hex(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        cache.set(f"sse_token:{token_hash}", str(request.user.pk), timeout=60)
        return Response({"token": token})


# ---------------------------------------------------------------------------
# SSE stream
# ---------------------------------------------------------------------------

MAX_CONNECTIONS_PER_USER = 1
HEARTBEAT_TIMEOUT = 15


class SSEStreamView(APIView):
    """
    GET /api/events/?token=<sse_token>
    Streams server-sent events for the authenticated user.
    """
    authentication_classes = []  # auth is handled via the one-time SSE token

    def get(self, request):
        token = request.GET.get("token", "").strip()
        if not token:
            return Response({"detail": "Missing token."}, status=401)

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        user_id = cache.get(f"sse_token:{token_hash}")
        if not user_id:
            return Response({"detail": "Invalid or expired token."}, status=401)

        cache.delete(f"sse_token:{token_hash}")

        if channels.active_count(user_id) >= MAX_CONNECTIONS_PER_USER:
            return Response(
                {"detail": "Too many concurrent SSE connections."},
                status=429,
            )

        resp = StreamingHttpResponse(
            streaming_content=self._event_stream(user_id),
            content_type="text/event-stream",
        )
        resp["Cache-Control"] = "no-cache"
        resp["X-Accel-Buffering"] = "no"
        return resp

    @staticmethod
    def _event_stream(user_id: str):
        q = channels.subscribe(user_id)
        try:
            while True:
                try:
                    payload = q.get(timeout=HEARTBEAT_TIMEOUT)
                    yield f"data: {json.dumps(payload)}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            channels.unsubscribe(user_id, q)
