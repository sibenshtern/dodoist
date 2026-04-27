from rest_framework import serializers

from .models import TaskSnapshot, UserMetric


class TaskSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskSnapshot
        fields = [
            "id",
            "project",
            "sprint",
            "snapshot_date",
            "total_tasks",
            "completed_tasks",
            "in_progress_tasks",
            "overdue_tasks",
            "total_story_points",
            "completed_story_points",
        ]


class UserMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMetric
        fields = [
            "id",
            "user",
            "project",
            "metric_date",
            "tasks_created",
            "tasks_completed",
            "tasks_assigned",
            "comments_posted",
            "logged_minutes",
        ]
