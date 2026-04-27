import uuid

from django.db import models
from django.utils import timezone as tz


class TaskSnapshot(models.Model):
    """Daily snapshot of task/story-point counts per project (and optionally per sprint)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="snapshots"
    )
    sprint = models.ForeignKey(
        "projects.Sprint",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="snapshots",
    )
    snapshot_date = models.DateField()
    total_tasks = models.PositiveIntegerField(default=0)
    completed_tasks = models.PositiveIntegerField(default=0)
    in_progress_tasks = models.PositiveIntegerField(default=0)
    overdue_tasks = models.PositiveIntegerField(default=0)
    total_story_points = models.PositiveIntegerField(default=0)
    completed_story_points = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=tz.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "task_snapshots"
        ordering = ["snapshot_date"]
        indexes = [
            models.Index(fields=["project", "snapshot_date"]),
            models.Index(fields=["sprint", "snapshot_date"]),
        ]

    def __str__(self):
        sprint_label = self.sprint.name if self.sprint_id else "–"
        return f"{self.project_id} / {sprint_label} / {self.snapshot_date}"


class UserMetric(models.Model):
    """Daily activity metrics per user, optionally scoped to a project."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="metrics"
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="user_metrics",
    )
    metric_date = models.DateField()
    tasks_created = models.PositiveIntegerField(default=0)
    tasks_completed = models.PositiveIntegerField(default=0)
    tasks_assigned = models.PositiveIntegerField(default=0)
    comments_posted = models.PositiveIntegerField(default=0)
    logged_minutes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=tz.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_metrics"
        ordering = ["metric_date"]
        indexes = [
            models.Index(fields=["user", "metric_date"]),
            models.Index(fields=["project", "metric_date"]),
        ]

    def __str__(self):
        return f"{self.user_id} / {self.project_id or 'global'} / {self.metric_date}"
