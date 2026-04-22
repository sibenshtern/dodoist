"""
In-process fan-out with optional Redis Pub/Sub bridge.

Subscribers call subscribe() to get a Queue, then block on queue.get(timeout=N).
Publishers call publish() which pushes to all local queues and, when a Redis URL
is configured via CELERY_BROKER_URL (and DEBUG is False), also pushes to Redis
so that other workers receive the event.
"""
import json
import queue
import threading
from typing import Any

_lock = threading.Lock()
_active_connections: dict[str, list[queue.Queue]] = {}


def subscribe(user_id: str) -> queue.Queue:
    q: queue.Queue = queue.Queue(maxsize=100)
    with _lock:
        _active_connections.setdefault(str(user_id), []).append(q)
    return q


def unsubscribe(user_id: str, q: queue.Queue) -> None:
    with _lock:
        subs = _active_connections.get(str(user_id), [])
        try:
            subs.remove(q)
        except ValueError:
            pass
        if not subs:
            _active_connections.pop(str(user_id), None)


def active_count(user_id: str) -> int:
    with _lock:
        return len(_active_connections.get(str(user_id), []))


def publish(user_id: str, payload: dict[str, Any]) -> None:
    """Push payload to all local subscribers and optionally to Redis."""
    with _lock:
        qs = list(_active_connections.get(str(user_id), []))
    for q in qs:
        try:
            q.put_nowait(payload)
        except queue.Full:
            pass

    _publish_redis(str(user_id), payload)


def _publish_redis(user_id: str, payload: dict[str, Any]) -> None:
    from django.conf import settings
    broker = getattr(settings, "CELERY_BROKER_URL", None)
    if not broker or getattr(settings, "DEBUG", True):
        return
    try:
        import redis as redis_lib
        r = redis_lib.from_url(broker)
        r.publish(f"sse:{user_id}", json.dumps(payload))
        r.close()
    except Exception:
        pass
