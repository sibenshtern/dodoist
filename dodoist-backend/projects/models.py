import uuid

from django.db import models
from django.utils import timezone as tz

from users.models import User


class WorkspacePlan(models.TextChoices):
    FREE = "free", "Free"
    PRO = "pro", "Pro"
    BUSINESS = "business", "Business"


class ProjectStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"
    DELETED = "deleted", "Deleted"


class ProjectType(models.TextChoices):
    SCRUM = "scrum", "Scrum"
    KANBAN = "kanban", "Kanban"
    PERSONAL = "personal", "Personal"


class ProjectRole(models.TextChoices):
    PO = "PO", "Product Owner"
    PM = "PM", "Project Manager"
    DEV = "DEV", "Developer"
    VW = "VW", "Viewer"
    GU = "GU", "Guest"


class SprintStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"


class BoardType(models.TextChoices):
    KANBAN = "kanban", "Kanban"
    SCRUM = "scrum", "Scrum"


class TaskStatus(models.TextChoices):
    BACKLOG = "backlog", "Backlog"
    TODO = "todo", "Todo"
    IN_PROGRESS = "in_progress", "In Progress"
    IN_REVIEW = "in_review", "In Review"
    DONE = "done", "Done"
    CANCELLED = "cancelled", "Cancelled"


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

class Workspace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name="owned_workspaces")
    plan = models.CharField(max_length=10, choices=WorkspacePlan.choices, default=WorkspacePlan.FREE)
    is_personal = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=tz.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workspaces"

    def __str__(self):
        return self.name


class WorkspaceMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="workspace_memberships")
    joined_at = models.DateTimeField(default=tz.now)

    class Meta:
        db_table = "workspace_members"
        unique_together = [("workspace", "user")]

    def __str__(self):
        return f"{self.user_id} in {self.workspace_id}"


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    key = models.CharField(max_length=10)
    color = models.CharField(max_length=20, blank=True, default="")
    icon_url = models.CharField(max_length=2048, blank=True, default="")
    status = models.CharField(max_length=10, choices=ProjectStatus.choices, default=ProjectStatus.ACTIVE)
    type = models.CharField(max_length=10, choices=ProjectType.choices, default=ProjectType.KANBAN)
    is_private = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_projects")
    created_at = models.DateTimeField(default=tz.now)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "projects"
        unique_together = [("workspace", "key")]

    def __str__(self):
        return f"{self.key} — {self.name}"


class ProjectMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="project_memberships")
    role = models.CharField(max_length=5, choices=ProjectRole.choices)
    invited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_invitations"
    )
    joined_at = models.DateTimeField(default=tz.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "project_members"
        unique_together = [("project", "user")]

    def __str__(self):
        return f"{self.user_id} in {self.project_id} as {self.role}"


class Label(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="labels")
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=20)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_labels")
    created_at = models.DateTimeField(default=tz.now)

    class Meta:
        db_table = "labels"
        unique_together = [("workspace", "name")]

    def __str__(self):
        return self.name


class Sprint(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="sprints")
    name = models.CharField(max_length=255)
    goal = models.TextField(blank=True, default="")
    status = models.CharField(max_length=10, choices=SprintStatus.choices, default=SprintStatus.PLANNED)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_sprints")
    created_at = models.DateTimeField(default=tz.now)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "sprints"

    def __str__(self):
        return f"{self.name} ({self.status})"


class Board(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="boards")
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=BoardType.choices, default=BoardType.KANBAN)
    is_default = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_boards")
    created_at = models.DateTimeField(default=tz.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "boards"

    def __str__(self):
        return f"{self.name} ({self.project_id})"


class BoardColumn(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="columns")
    name = models.CharField(max_length=100)
    status_mapping = models.CharField(max_length=15, choices=TaskStatus.choices)
    position = models.PositiveIntegerField()
    wip_limit = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=tz.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "board_columns"
        ordering = ["position"]

    def __str__(self):
        return f"{self.name} (pos={self.position})"
