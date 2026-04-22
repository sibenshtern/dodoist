from django.urls import path

from .views import (
    ActiveWorkspaceView,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    MeView,
    NotificationDetailView,
    NotificationListView,
    NotificationReadAllView,
    RefreshView,
    RegisterView,
    ResendVerificationView,
    ResetPasswordView,
    UserDetailView,
    UserListView,
    UserPreferencesView,
    UserSessionDetailView,
    UserSessionListView,
    VerifyEmailView,
)

urlpatterns = [
    # Auth
    path("api/auth/register", RegisterView.as_view(), name="auth-register"),
    path("api/auth/login", LoginView.as_view(), name="auth-login"),
    path("api/auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("api/auth/refresh", RefreshView.as_view(), name="auth-refresh"),
    path("api/auth/verify-email", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("api/auth/resend-verification", ResendVerificationView.as_view(), name="auth-resend-verification"),
    path("api/auth/forgot-password", ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("api/auth/reset-password", ResetPasswordView.as_view(), name="auth-reset-password"),
    # Users
    path("api/users/me", MeView.as_view(), name="users-me"),
    path("api/users/me/active-workspace/", ActiveWorkspaceView.as_view(), name="users-active-workspace"),
    path("api/users/", UserListView.as_view(), name="user-list"),
    path("api/users/<uuid:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("api/users/<uuid:pk>/preferences/", UserPreferencesView.as_view(), name="user-preferences"),
    path("api/users/<uuid:pk>/sessions/", UserSessionListView.as_view(), name="user-sessions"),
    path("api/users/<uuid:pk>/sessions/<uuid:session_id>/", UserSessionDetailView.as_view(), name="user-session-detail"),
    # Notifications
    path("api/notifications/", NotificationListView.as_view(), name="notification-list"),
    path("api/notifications/read-all/", NotificationReadAllView.as_view(), name="notification-read-all"),
    path("api/notifications/<uuid:pk>/", NotificationDetailView.as_view(), name="notification-detail"),
]
