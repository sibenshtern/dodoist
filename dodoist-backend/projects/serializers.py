from rest_framework import serializers

from .models import Workspace, WorkspaceMember, WorkspacePlan


class UserBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    display_name = serializers.CharField()
    email = serializers.EmailField()


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
