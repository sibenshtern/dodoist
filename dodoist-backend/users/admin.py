from django.contrib import admin

from .models import Notification, User, UserPreferences, UserSession


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "display_name", "global_role", "is_active", "created_at")
    list_filter = ("global_role", "is_active")
    search_fields = ("email", "display_name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "last_login")
    exclude = ("password",)


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "ip_address", "expires_at", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "ip_address")
    ordering = ("-created_at",)
    readonly_fields = ("token_hash", "refresh_token_hash", "created_at")


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ("user", "theme", "language", "digest_frequency", "default_view")
    search_fields = ("user__email",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("type", "recipient", "actor", "is_read", "created_at")
    list_filter = ("type", "is_read")
    search_fields = ("recipient__email", "message")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "read_at")
