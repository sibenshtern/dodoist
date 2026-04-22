from rest_framework import serializers


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    display_name = serializers.CharField(min_length=2, max_length=255)
    timezone = serializers.CharField(max_length=64, default="UTC")
    invite_token = serializers.CharField(required=False, allow_blank=True, default="")


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class AuthUserSerializer(serializers.Serializer):
    """Read-only representation of a user returned in auth responses."""
    id = serializers.UUIDField()
    email = serializers.EmailField()
    display_name = serializers.CharField()


class ActiveWorkspaceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.CharField()
    name = serializers.CharField()
    is_personal = serializers.BooleanField()


class UserProfileSerializer(serializers.Serializer):
    """Full user profile returned by GET /api/users/me."""
    id = serializers.UUIDField()
    email = serializers.EmailField()
    display_name = serializers.CharField()
    avatar_url = serializers.CharField(allow_null=True)
    timezone = serializers.CharField()
    active_workspace = serializers.SerializerMethodField()

    def get_active_workspace(self, obj):
        ws = obj.active_workspace
        if ws is None:
            return None
        return ActiveWorkspaceSerializer(ws).data


class UserListSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    display_name = serializers.CharField()
    avatar_url = serializers.CharField()
    timezone = serializers.CharField()
    global_role = serializers.CharField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class UserUpdateSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=255, required=False)
    avatar_url = serializers.CharField(max_length=2048, required=False, allow_blank=True)
    timezone = serializers.CharField(max_length=64, required=False)
    global_role = serializers.CharField(required=False)

    def validate_avatar_url(self, value):
        if value and not value.startswith("https://"):
            raise serializers.ValidationError("avatar_url must use HTTPS.")
        return value

    def validate_global_role(self, value):
        from users.models import GlobalRole
        valid = [c[0] for c in GlobalRole.choices]
        if value not in valid:
            raise serializers.ValidationError(f"Must be one of: {valid}")
        return value


class UserPreferencesSerializer(serializers.Serializer):
    theme = serializers.CharField()
    language = serializers.CharField()
    notification_channels = serializers.JSONField()
    digest_frequency = serializers.CharField()
    default_view = serializers.CharField()
    updated_at = serializers.DateTimeField()


class UserPreferencesUpdateSerializer(serializers.Serializer):
    theme = serializers.ChoiceField(
        choices=["light", "dark", "system"], required=False
    )
    language = serializers.CharField(max_length=10, required=False)
    notification_channels = serializers.JSONField(required=False)
    digest_frequency = serializers.ChoiceField(
        choices=["realtime", "daily", "weekly"], required=False
    )
    default_view = serializers.ChoiceField(
        choices=["list", "board", "calendar"], required=False
    )


class NotificationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    type = serializers.CharField()
    message = serializers.CharField()
    task_id = serializers.UUIDField(allow_null=True)
    project_id = serializers.UUIDField(allow_null=True)
    is_read = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    read_at = serializers.DateTimeField(allow_null=True)
    actor = serializers.SerializerMethodField()

    def get_actor(self, obj):
        if obj.actor_id:
            return {"id": str(obj.actor_id), "display_name": obj.actor.display_name}
        return None
