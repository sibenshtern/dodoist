from django.contrib import admin
from django.contrib import messages

from .models import GlobalRole, Notification, User, UserPreferences, UserSession


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "display_name", "global_role", "is_active", "email_verified", "created_at")
    list_filter = ("global_role", "is_active", "email_verified")
    search_fields = ("email", "display_name")
    ordering = ("-created_at",)
    readonly_fields = (
        "created_at", "last_login", "updated_at",
        "token_hash_display",
        "verification_token_hash", "password_reset_token_hash",
    )
    exclude = ("password",)

    def token_hash_display(self, obj):
        return "*** hidden ***"
    token_hash_display.short_description = "Token hash"

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return super().has_change_permission(request)
        # Non-SA admins cannot edit SA accounts
        if obj.global_role == GlobalRole.SA and request.user.global_role != GlobalRole.SA:
            return False
        return super().has_change_permission(request, obj)

    def save_model(self, request, obj, form, change):
        # Prevent non-SA admins from promoting anyone to SA
        if obj.global_role == GlobalRole.SA and request.user.global_role != GlobalRole.SA:
            messages.error(request, "Only System Admins can assign the SA role.")
            obj.global_role = GlobalRole.GA
        # Prevent admins from demoting their own account
        if change and obj.pk == request.user.pk:
            original = User.objects.get(pk=obj.pk)
            if original.global_role != obj.global_role:
                messages.warning(request, "You cannot change your own role.")
                obj.global_role = original.global_role
        super().save_model(request, obj, form, change)


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
