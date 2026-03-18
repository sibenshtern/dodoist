import uuid

from django.db import models
from django.utils import timezone as tz

from projects.models import BoardColumn, Label, Project, Sprint, TaskStatus
from users.models import User


class TaskType(models.TextChoices):
    TASK = "task", "Task"
    BUG = "bug", "Bug"
    STORY = "story", "Story"
    EPIC = "epic", "Epic"
    PERSONAL = "personal", "Personal"


class TaskPriority(models.TextChoices):
    CRITICAL = "critical", "Critical"
    HIGH = "high", "High"
    MEDIUM = "medium", "Medium"
    LOW = "low", "Low"
    NONE = "none", "None"


class DependencyType(models.TextChoices):
    BLOCKS = "blocks", "Blocks"
    IS_BLOCKED_BY = "is_blocked_by", "Is Blocked By"
    RELATES_TO = "relates_to", "Relates To"
    DUPLICATES = "duplicates", "Duplicates"
    IS_DUPLICATED_BY = "is_duplicated_by", "Is Duplicated By"


class CustomFieldType(models.TextChoices):
    TEXT = "text", "Text"
    NUMBER = "number", "Number"
    DATE = "date", "Date"
    SELECT = "select", "Select"
    MULTI_SELECT = "multi_select", "Multi Select"
    USER = "user", "User"
    URL = "url", "URL"


class ActivityEntityType(models.TextChoices):
    TASK = "task", "Task"
    PROJECT = "project", "Project"
    SPRINT = "sprint", "Sprint"
    COMMENT = "comment", "Comment"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    parent_task = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="subtasks"
    )
    sprint = models.ForeignKey(
        Sprint, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks"
    )
    board_column = models.ForeignKey(
        BoardColumn, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks"
    )
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_tasks")
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tasks"
    )
    title = models.CharField(max_length=500)
    description = models.JSONField(null=True, blank=True, help_text="Rich text as ProseMirror JSON")
    type = models.CharField(max_length=10, choices=TaskType.choices, default=TaskType.TASK)
    status = models.CharField(max_length=15, choices=TaskStatus.choices, default=TaskStatus.BACKLOG)
    priority = models.CharField(max_length=10, choices=TaskPriority.choices, default=TaskPriority.NONE)
    story_points = models.PositiveIntegerField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    reminder_at = models.DateTimeField(null=True, blank=True)
    position = models.FloatField(default=0)
    is_private = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=tz.now)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tasks"
        indexes = [
            models.Index(fields=["project"]),
            models.Index(fields=["assigned_to"]),
            models.Index(fields=["status"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["deleted_at"]),
        ]

    def __str__(self):
        return self.title

    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def is_completed(self) -> bool:
        return self.status == TaskStatus.DONE

    def is_overdue(self) -> bool:
        if self.is_completed() or self.due_date is None:
            return False
        return tz.now() > self.due_date


class TaskAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="co_assignments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="co_assigned_tasks")
    assigned_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="given_assignments")
    assigned_at = models.DateTimeField(default=tz.now)

    class Meta:
        db_table = "task_assignments"
        unique_together = [("task", "user")]


class TaskLabel(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="task_labels")
    label = models.ForeignKey(Label, on_delete=models.CASCADE, related_name="task_labels")

    class Meta:
        db_table = "task_labels"
        unique_together = [("task", "label")]


class TaskDependency(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="dependencies")
    depends_on_task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="dependents")
    type = models.CharField(max_length=20, choices=DependencyType.choices)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_dependencies")
    created_at = models.DateTimeField(default=tz.now)

    class Meta:
        db_table = "task_dependencies"


class TaskGuestAccess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="guest_accesses")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="guest_task_accesses")
    granted_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="granted_accesses")
    granted_at = models.DateTimeField(default=tz.now)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "task_guest_access"
        unique_together = [("task", "user")]


class CustomField(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="custom_fields")
    name = models.CharField(max_length=100)
    field_type = models.CharField(max_length=15, choices=CustomFieldType.choices)
    options = models.JSONField(null=True, blank=True, help_text="For select/multi_select types")
    is_required = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_custom_fields")
    created_at = models.DateTimeField(default=tz.now)

    class Meta:
        db_table = "custom_fields"


class TaskCustomFieldValue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="custom_field_values")
    custom_field = models.ForeignKey(CustomField, on_delete=models.CASCADE, related_name="values")
    value = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "task_custom_field_values"
        unique_together = [("task", "custom_field")]


# ---------------------------------------------------------------------------
# Collaboration
# ---------------------------------------------------------------------------

class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name="comments")
    parent_comment = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    body = models.JSONField(help_text="Rich text as ProseMirror JSON")
    is_edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=tz.now)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "comments"

    def __str__(self):
        return f"Comment by {self.author_id} on {self.task_id}"

    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class ActivityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_type = models.CharField(max_length=10, choices=ActivityEntityType.choices)
    entity_id = models.UUIDField()
    actor = models.ForeignKey(User, on_delete=models.PROTECT, related_name="activity_logs")
    action = models.CharField(max_length=50)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, null=True, blank=True, related_name="activity_logs"
    )
    created_at = models.DateTimeField(default=tz.now)

    class Meta:
        db_table = "activity_log"
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["project"]),
            models.Index(fields=["actor"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.action} on {self.entity_type}:{self.entity_id}"
