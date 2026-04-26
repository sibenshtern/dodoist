from rest_framework import serializers

from projects.models import BoardColumn, Label, Project, ProjectStatus, Sprint, TaskStatus
from users.models import User

from .models import Attachment, DependencyType, Task, TaskAssignment, TaskDependency, TaskGuestAccess, TaskLabel, TaskPriority, TaskType
from .services import TaskService


class UserBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    display_name = serializers.CharField()
    email = serializers.EmailField()


class LabelBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField(source='label.id')
    name = serializers.CharField(source='label.name')
    color = serializers.CharField(source='label.color')


class TaskSerializer(serializers.ModelSerializer):
    created_by = UserBriefSerializer(read_only=True)
    assigned_to = UserBriefSerializer(read_only=True)
    labels = LabelBriefSerializer(source='task_labels', many=True, read_only=True)
    is_deleted = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "project",
            "parent_task",
            "sprint",
            "board_column",
            "created_by",
            "assigned_to",
            "labels",
            "title",
            "description",
            "type",
            "status",
            "priority",
            "story_points",
            "due_date",
            "start_date",
            "reminder_at",
            "position",
            "is_private",
            "created_at",
            "updated_at",
            "completed_at",
            "is_deleted",
            "is_overdue",
        ]

    def get_is_deleted(self, obj: Task) -> bool:
        return obj.is_deleted()

    def get_is_overdue(self, obj: Task) -> bool:
        return obj.is_overdue()


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

class TaskCreateSerializer(serializers.Serializer):
    project_id = serializers.UUIDField()
    title = serializers.CharField(max_length=500)
    task_type = serializers.ChoiceField(choices=TaskType.choices, default=TaskType.TASK)
    priority = serializers.ChoiceField(choices=TaskPriority.choices, default=TaskPriority.NONE)
    status = serializers.ChoiceField(choices=TaskStatus.choices, required=False)
    description = serializers.JSONField(required=False, allow_null=True)
    assigned_to_id = serializers.UUIDField(required=False, allow_null=True)
    sprint_id = serializers.UUIDField(required=False, allow_null=True)
    board_column_id = serializers.UUIDField(required=False, allow_null=True)
    parent_task_id = serializers.UUIDField(required=False, allow_null=True)
    story_points = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    start_date = serializers.DateTimeField(required=False, allow_null=True)
    reminder_at = serializers.DateTimeField(required=False, allow_null=True)
    is_private = serializers.BooleanField(default=False)

    def validate_project_id(self, value):
        try:
            project = Project.objects.get(pk=value)
        except Project.DoesNotExist:
            raise serializers.ValidationError("Project not found.")
        if project.status != ProjectStatus.ACTIVE:
            raise serializers.ValidationError("Project is not active.")
        return project  # Replace UUID with the actual object

    def validate(self, data):
        errors = {}
        project = data.get("project_id")  # Already a Project object after field validation

        assigned_to_id = data.pop("assigned_to_id", None)
        if assigned_to_id is not None:
            try:
                data["assigned_to"] = User.objects.get(pk=assigned_to_id, is_active=True)
            except User.DoesNotExist:
                errors["assigned_to_id"] = "User not found."

        sprint_id = data.pop("sprint_id", None)
        if sprint_id is not None:
            try:
                data["sprint"] = Sprint.objects.get(pk=sprint_id, project=project)
            except Sprint.DoesNotExist:
                errors["sprint_id"] = "Sprint not found in this project."

        board_column_id = data.pop("board_column_id", None)
        if board_column_id is not None:
            try:
                data["board_column"] = BoardColumn.objects.get(pk=board_column_id)
            except BoardColumn.DoesNotExist:
                errors["board_column_id"] = "Board column not found."

        parent_task_id = data.pop("parent_task_id", None)
        if parent_task_id is not None:
            try:
                data["parent_task"] = Task.objects.get(pk=parent_task_id, deleted_at__isnull=True)
            except Task.DoesNotExist:
                errors["parent_task_id"] = "Parent task not found."

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def create(self, validated_data):
        creator = validated_data.pop("creator")
        project = validated_data.pop("project_id")
        task_type = validated_data.pop("task_type", TaskType.TASK)
        priority = validated_data.pop("priority", TaskPriority.NONE)
        title = validated_data.pop("title")

        return TaskService.create_task(
            project=project,
            creator=creator,
            title=title,
            task_type=task_type,
            priority=priority,
            **validated_data,
        )


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

class TaskUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=500, required=False)
    description = serializers.JSONField(required=False, allow_null=True)
    type = serializers.ChoiceField(choices=TaskType.choices, required=False)
    status = serializers.ChoiceField(choices=TaskStatus.choices, required=False)
    priority = serializers.ChoiceField(choices=TaskPriority.choices, required=False)
    assigned_to_id = serializers.UUIDField(required=False, allow_null=True)
    sprint_id = serializers.UUIDField(required=False, allow_null=True)
    story_points = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    start_date = serializers.DateTimeField(required=False, allow_null=True)
    reminder_at = serializers.DateTimeField(required=False, allow_null=True)
    is_private = serializers.BooleanField(required=False)

    def validate_assigned_to_id(self, value):
        if value is None:
            return None
        try:
            return User.objects.get(pk=value, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")

    def validate_sprint_id(self, value):
        if value is None:
            return None
        try:
            return Sprint.objects.get(pk=value)
        except Sprint.DoesNotExist:
            raise serializers.ValidationError("Sprint not found.")

    def validate(self, data):
        # Ensure the sprint belongs to the same project as the task
        sprint = data.get("sprint_id")
        if sprint is not None and self.instance:
            if sprint.project_id != self.instance.project_id:
                raise serializers.ValidationError(
                    {"sprint_id": "Sprint does not belong to this task's project."}
                )
        return data

    def update(self, instance: Task, validated_data: dict) -> Task:
        actor = validated_data.pop("actor")
        fields_to_save = []

        # Status: delegate to service so completed_at is managed correctly
        if "status" in validated_data:
            TaskService.update_status(instance, validated_data.pop("status"), actor)

        # Assignee: delegate to service for logging; handle unassign separately
        if "assigned_to_id" in validated_data:
            user = validated_data.pop("assigned_to_id")  # User object or None
            if user is not None:
                TaskService.assign_user(instance, user, actor)
            else:
                instance.assigned_to = None
                fields_to_save.append("assigned_to")

        # Sprint: field-level validation already resolved UUID to a Sprint object
        if "sprint_id" in validated_data:
            instance.sprint = validated_data.pop("sprint_id")
            fields_to_save.append("sprint")

        # Apply remaining simple field updates directly
        for field, value in validated_data.items():
            setattr(instance, field, value)
            fields_to_save.append(field)

        if fields_to_save:
            instance.save(update_fields=fields_to_save + ["updated_at"])

        return instance


# ---------------------------------------------------------------------------
# Subtasks / nested task brief
# ---------------------------------------------------------------------------

class TaskBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    status = serializers.CharField()
    type = serializers.CharField()


# ---------------------------------------------------------------------------
# Assignments (co-assignees)
# ---------------------------------------------------------------------------

class TaskAssignmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user = UserBriefSerializer()
    assigned_by = UserBriefSerializer()
    assigned_at = serializers.DateTimeField()


class TaskAssignmentAddSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()

    def validate_user_id(self, value):
        try:
            return User.objects.get(pk=value, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")


# ---------------------------------------------------------------------------
# Task labels
# ---------------------------------------------------------------------------

class TaskLabelSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="label.id")
    name = serializers.CharField(source="label.name")
    color = serializers.CharField(source="label.color")


class TaskLabelAddSerializer(serializers.Serializer):
    label_id = serializers.UUIDField()

    def validate_label_id(self, value):
        try:
            return Label.objects.get(pk=value)
        except Label.DoesNotExist:
            raise serializers.ValidationError("Label not found.")


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

class TaskDependencySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    depends_on_task = TaskBriefSerializer()
    type = serializers.CharField()
    created_by = UserBriefSerializer()
    created_at = serializers.DateTimeField()


class TaskDependencyCreateSerializer(serializers.Serializer):
    depends_on_task_id = serializers.UUIDField()
    type = serializers.ChoiceField(choices=DependencyType.choices)

    def validate_depends_on_task_id(self, value):
        try:
            return Task.objects.get(pk=value, deleted_at__isnull=True)
        except Task.DoesNotExist:
            raise serializers.ValidationError("Task not found.")


# ---------------------------------------------------------------------------
# Guest access
# ---------------------------------------------------------------------------

class TaskGuestAccessSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user = UserBriefSerializer()
    granted_by = UserBriefSerializer()
    granted_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField(allow_null=True)


class TaskGuestAccessCreateSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    expires_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate_user_id(self, value):
        try:
            return User.objects.get(pk=value, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")


# ---------------------------------------------------------------------------
# Project-nested task creation (project comes from URL, not body)
# ---------------------------------------------------------------------------

class ProjectTaskCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=500)
    task_type = serializers.ChoiceField(choices=TaskType.choices, default=TaskType.TASK)
    priority = serializers.ChoiceField(choices=TaskPriority.choices, default=TaskPriority.NONE)
    status = serializers.ChoiceField(choices=TaskStatus.choices, required=False)
    description = serializers.JSONField(required=False, allow_null=True)
    assigned_to_id = serializers.UUIDField(required=False, allow_null=True)
    sprint_id = serializers.UUIDField(required=False, allow_null=True)
    board_column_id = serializers.UUIDField(required=False, allow_null=True)
    parent_task_id = serializers.UUIDField(required=False, allow_null=True)
    story_points = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    start_date = serializers.DateTimeField(required=False, allow_null=True)
    is_private = serializers.BooleanField(default=False)
    reminder_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, data):
        errors = {}
        project = self.context.get("project")

        assigned_to_id = data.pop("assigned_to_id", None)
        if assigned_to_id is not None:
            try:
                data["assigned_to"] = User.objects.get(pk=assigned_to_id, is_active=True)
            except User.DoesNotExist:
                errors["assigned_to_id"] = "User not found."

        sprint_id = data.pop("sprint_id", None)
        if sprint_id is not None:
            try:
                data["sprint"] = Sprint.objects.get(pk=sprint_id, project=project)
            except Sprint.DoesNotExist:
                errors["sprint_id"] = "Sprint not found in this project."

        board_column_id = data.pop("board_column_id", None)
        if board_column_id is not None:
            try:
                data["board_column"] = BoardColumn.objects.get(pk=board_column_id)
            except BoardColumn.DoesNotExist:
                errors["board_column_id"] = "Board column not found."

        parent_task_id = data.pop("parent_task_id", None)
        if parent_task_id is not None:
            try:
                data["parent_task"] = Task.objects.get(pk=parent_task_id, deleted_at__isnull=True)
            except Task.DoesNotExist:
                errors["parent_task_id"] = "Parent task not found."

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def create(self, validated_data):
        creator = validated_data.pop("creator")
        project = validated_data.pop("project")
        task_type = validated_data.pop("task_type", TaskType.TASK)
        priority = validated_data.pop("priority", TaskPriority.NONE)
        title = validated_data.pop("title")

        return TaskService.create_task(
            project=project,
            creator=creator,
            title=title,
            task_type=task_type,
            priority=priority,
            **validated_data,
        )


# ---------------------------------------------------------------------------
# Comment serializers
# ---------------------------------------------------------------------------

class CommentAuthorSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    display_name = serializers.CharField()
    avatar_url = serializers.CharField()


class CommentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    task_id = serializers.UUIDField()
    author = CommentAuthorSerializer()
    parent_comment_id = serializers.UUIDField(allow_null=True)
    body = serializers.JSONField()
    is_edited = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class CommentCreateSerializer(serializers.Serializer):
    body = serializers.JSONField()
    parent_comment_id = serializers.UUIDField(required=False, allow_null=True)


class CommentUpdateSerializer(serializers.Serializer):
    body = serializers.JSONField()


# ---------------------------------------------------------------------------
# Activity serializers
# ---------------------------------------------------------------------------

class ActivityActorSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    display_name = serializers.CharField()


class ActivityLogSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    entity_type = serializers.CharField()
    entity_id = serializers.UUIDField()
    actor = ActivityActorSerializer()
    action = serializers.CharField()
    old_value = serializers.JSONField(allow_null=True)
    new_value = serializers.JSONField(allow_null=True)
    created_at = serializers.DateTimeField()


# ---------------------------------------------------------------------------
# Custom field serializers
# ---------------------------------------------------------------------------

class CustomFieldSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    project_id = serializers.UUIDField()
    name = serializers.CharField()
    field_type = serializers.CharField()
    options = serializers.JSONField(allow_null=True)
    is_required = serializers.BooleanField()
    position = serializers.IntegerField()
    created_by = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()

    def get_created_by(self, obj):
        return {"id": str(obj.created_by_id), "display_name": obj.created_by.display_name}


class CustomFieldCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    field_type = serializers.ChoiceField(
        choices=["text", "number", "date", "select", "multi_select", "user", "url"]
    )
    options = serializers.JSONField(required=False, allow_null=True)
    is_required = serializers.BooleanField(default=False)
    position = serializers.IntegerField(default=0, min_value=0)


class CustomFieldUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    options = serializers.JSONField(required=False, allow_null=True)
    is_required = serializers.BooleanField(required=False)
    position = serializers.IntegerField(required=False, min_value=0)


class TaskCustomFieldValueSerializer(serializers.Serializer):
    custom_field_id = serializers.UUIDField()
    field_name = serializers.SerializerMethodField()
    field_type = serializers.SerializerMethodField()
    value = serializers.CharField(allow_blank=True)
    updated_at = serializers.DateTimeField()

    def get_field_name(self, obj):
        return obj.custom_field.name

    def get_field_type(self, obj):
        return obj.custom_field.field_type


class TaskCustomFieldValueSetSerializer(serializers.Serializer):
    value = serializers.CharField(allow_blank=True)


# ---------------------------------------------------------------------------
# TimeLog serializers
# ---------------------------------------------------------------------------

class TimeLogSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user = UserBriefSerializer()
    logged_minutes = serializers.IntegerField()
    logged_date = serializers.DateField()
    description = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()


class TimeLogCreateSerializer(serializers.Serializer):
    logged_minutes = serializers.IntegerField(min_value=1, max_value=1440)
    logged_date = serializers.DateField()
    description = serializers.CharField(required=False, allow_blank=True, default="")


class TimeLogUpdateSerializer(serializers.Serializer):
    logged_minutes = serializers.IntegerField(min_value=1, max_value=1440, required=False)
    logged_date = serializers.DateField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)


# ---------------------------------------------------------------------------
# Reaction serializers
# ---------------------------------------------------------------------------

class ReactionSerializer(serializers.Serializer):
    emoji = serializers.CharField()
    user = UserBriefSerializer()
    created_at = serializers.DateTimeField()


# ---------------------------------------------------------------------------
# Attachment serializers
# ---------------------------------------------------------------------------

class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = UserBriefSerializer(read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ["id", "filename", "file_size_bytes", "mime_type", "download_url", "uploaded_by", "created_at"]

    def get_download_url(self, obj):
        from django.core.files.storage import default_storage
        request = self.context.get("request")
        url = default_storage.url(obj.storage_key)
        if request:
            return request.build_absolute_uri(url)
        return url
