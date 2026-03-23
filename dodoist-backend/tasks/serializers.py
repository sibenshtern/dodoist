from rest_framework import serializers

from projects.models import BoardColumn, Project, ProjectStatus, Sprint, TaskStatus
from users.models import User

from .models import Task, TaskPriority, TaskType
from .services import TaskService


class UserBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    display_name = serializers.CharField()
    email = serializers.EmailField()


class TaskSerializer(serializers.ModelSerializer):
    created_by = UserBriefSerializer(read_only=True)
    assigned_to = UserBriefSerializer(read_only=True)
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
