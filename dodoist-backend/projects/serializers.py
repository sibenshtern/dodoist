import re

from rest_framework import serializers

from users.models import User

from .models import (
    Label,
    Project,
    ProjectMember,
    ProjectRole,
    ProjectType,
    SprintStatus,
    Workspace,
    WorkspacePlan,
)


class UserBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    display_name = serializers.CharField()
    email = serializers.EmailField()


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

class WorkspaceSerializer(serializers.ModelSerializer):
    owner = UserBriefSerializer(read_only=True)

    class Meta:
        model = Workspace
        fields = [
            "id",
            "slug",
            "name",
            "description",
            "owner",
            "plan",
            "is_personal",
            "created_at",
            "updated_at",
        ]


class WorkspaceCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=100, required=False, default="")
    description = serializers.CharField(required=False, allow_blank=True, default="")
    plan = serializers.ChoiceField(choices=WorkspacePlan.choices, default=WorkspacePlan.FREE)

    def validate_slug(self, value):
        if value and Workspace.objects.filter(slug=value).exists():
            raise serializers.ValidationError("This slug is already taken.")
        return value


class WorkspaceUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    plan = serializers.ChoiceField(choices=WorkspacePlan.choices, required=False)

    def update(self, instance: Workspace, validated_data: dict) -> Workspace:
        fields_to_save = []
        for field, value in validated_data.items():
            setattr(instance, field, value)
            fields_to_save.append(field)
        if fields_to_save:
            instance.save(update_fields=fields_to_save + ["updated_at"])
        return instance


class WorkspaceMemberSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user = UserBriefSerializer()
    joined_at = serializers.DateTimeField()


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

class SprintBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    status = serializers.CharField()
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(allow_null=True)


class ProjectSerializer(serializers.ModelSerializer):
    created_by = UserBriefSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    active_sprint = serializers.SerializerMethodField()
    current_user_role = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "workspace",
            "name",
            "description",
            "key",
            "color",
            "icon_url",
            "status",
            "type",
            "is_private",
            "created_by",
            "created_at",
            "updated_at",
            "archived_at",
            "member_count",
            "active_sprint",
            "current_user_role",
        ]

    def get_member_count(self, obj: Project) -> int:
        return len(obj.members.all())

    def get_active_sprint(self, obj: Project):
        active_sprints = getattr(obj, "active_sprints", None)
        if active_sprints is not None:
            sprint = active_sprints[0] if active_sprints else None
        else:
            sprint = obj.sprints.filter(status=SprintStatus.ACTIVE).first()
        return SprintBriefSerializer(sprint).data if sprint else None

    def get_current_user_role(self, obj: Project):
        request = self.context.get("request")
        if not request:
            return None
        for m in obj.members.all():
            if m.user_id == request.user.pk:
                return m.role
        return None


class ProjectCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    key = serializers.CharField(max_length=10)
    type = serializers.ChoiceField(choices=ProjectType.choices)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    color = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    is_private = serializers.BooleanField(default=False)

    def validate_key(self, value):
        upper = value.upper()
        if not re.match(r"^[A-Z0-9]{2,10}$", upper):
            raise serializers.ValidationError(
                "Key must be 2-10 characters using only letters and digits (A-Z, 0-9)."
            )
        return upper


class ProjectUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    color = serializers.CharField(max_length=20, required=False, allow_blank=True)
    icon_url = serializers.CharField(max_length=2048, required=False, allow_blank=True)
    is_private = serializers.BooleanField(required=False)

    def validate_icon_url(self, value):
        if value and not value.startswith("https://"):
            raise serializers.ValidationError("icon_url must use HTTPS.")
        return value

    def update(self, instance: Project, validated_data: dict) -> Project:
        fields_to_save = []
        for field, value in validated_data.items():
            setattr(instance, field, value)
            fields_to_save.append(field)
        if fields_to_save:
            instance.save(update_fields=fields_to_save + ["updated_at"])
        return instance


class ProjectMemberSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user = UserBriefSerializer()
    role = serializers.CharField()
    invited_by = UserBriefSerializer(allow_null=True)
    joined_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ProjectMemberAddSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=ProjectRole.choices)

    def validate_user_id(self, value):
        try:
            return User.objects.get(pk=value, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")


class ProjectMemberUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=ProjectRole.choices)


# ---------------------------------------------------------------------------
# Label
# ---------------------------------------------------------------------------

class LabelSerializer(serializers.ModelSerializer):
    created_by = UserBriefSerializer(read_only=True)

    class Meta:
        model = Label
        fields = ["id", "workspace", "name", "color", "created_by", "created_at"]


class LabelCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    color = serializers.CharField(max_length=20)


class LabelUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    color = serializers.CharField(max_length=20, required=False)

    def update(self, instance: Label, validated_data: dict) -> Label:
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save(update_fields=list(validated_data.keys()))
        return instance
