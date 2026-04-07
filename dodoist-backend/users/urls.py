from django.urls import path

from .views import (
    LoginView, LogoutView, MeView, NotificationDetailView, NotificationListView,
    NotificationReadAllView, RefreshView, RegisterView, UserDetailView, UserListView,
    UserPreferencesView,
)

urlpatterns = [
    path("api/auth/register", RegisterView.as_view(), name="auth-register"),
    path("api/auth/login", LoginView.as_view(), name="auth-login"),
    path("api/auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("api/auth/refresh", RefreshView.as_view(), name="auth-refresh"),
    path("api/users/me", MeView.as_view(), name="users-me"),
    path("api/users/", UserListView.as_view(), name="user-list"),
    path("api/users/<uuid:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("api/users/<uuid:pk>/preferences/", UserPreferencesView.as_view(), name="user-preferences"),
    # Notifications (must come before <uuid:pk> patterns)
    path("api/notifications/", NotificationListView.as_view(), name="notification-list"),
    path("api/notifications/read-all/", NotificationReadAllView.as_view(), name="notification-read-all"),
    path("api/notifications/<uuid:pk>/", NotificationDetailView.as_view(), name="notification-detail"),
]
