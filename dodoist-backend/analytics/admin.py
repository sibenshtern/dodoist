from django.contrib import admin

from .models import TaskSnapshot, UserMetric


@admin.register(TaskSnapshot)
class TaskSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "project", "sprint", "snapshot_date",
        "total_tasks", "completed_tasks", "in_progress_tasks", "overdue_tasks",
        "total_story_points", "completed_story_points",
    )
    list_filter = ("snapshot_date",)
    search_fields = ("project__name", "sprint__name")
    ordering = ("-snapshot_date",)
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("project", "sprint")
    date_hierarchy = "snapshot_date"


@admin.register(UserMetric)
class UserMetricAdmin(admin.ModelAdmin):
    list_display = (
        "user", "project", "metric_date",
        "tasks_created", "tasks_completed", "tasks_assigned",
        "comments_posted", "logged_minutes",
    )
    list_filter = ("metric_date",)
    search_fields = ("user__email", "project__name")
    ordering = ("-metric_date",)
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("user", "project")
    date_hierarchy = "metric_date"
