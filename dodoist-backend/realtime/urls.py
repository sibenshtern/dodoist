from django.urls import path

from .views import SSEStreamView, SSETokenView

urlpatterns = [
    path("api/events/", SSEStreamView.as_view(), name="sse-stream"),
    path("api/auth/sse-token/", SSETokenView.as_view(), name="sse-token"),
]
