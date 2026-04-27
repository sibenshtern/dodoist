"""
Management command: generate_analytics_snapshots

Generates TaskSnapshot and UserMetric rows for a given date (default: today).
Run nightly via Celery beat at 00:15 UTC, or manually for backfill:

    python manage.py generate_analytics_snapshots
    python manage.py generate_analytics_snapshots --since=2026-01-01
"""

from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q, Sum

from analytics.models import TaskSnapshot, UserMetric
from projects.models import Project, ProjectMember, ProjectStatus, Sprint, SprintStatus
from tasks.models import Comment, Task, TimeLog
from users.models import User


def _date_range(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _snapshot_for(project, sprint, snapshot_date):
    """Compute and upsert a TaskSnapshot row."""
    qs = Task.objects.filter(project=project, deleted_at__isnull=True)
    if sprint is not None:
        qs = qs.filter(sprint=sprint)

    total = qs.count()
    completed = qs.filter(status="done").count()
    in_progress = qs.filter(status="in_progress").count()
    overdue = qs.filter(
        due_date__date__lte=snapshot_date
    ).exclude(status__in=["done", "cancelled"]).count()

    agg = qs.aggregate(
        total_sp=Sum("story_points"),
        completed_sp=Sum("story_points", filter=Q(status="done")),
    )

    TaskSnapshot.objects.update_or_create(
        project=project,
        sprint=sprint,
        snapshot_date=snapshot_date,
        defaults={
            "total_tasks": total,
            "completed_tasks": completed,
            "in_progress_tasks": in_progress,
            "overdue_tasks": overdue,
            "total_story_points": agg["total_sp"] or 0,
            "completed_story_points": agg["completed_sp"] or 0,
        },
    )


def _user_metrics_for(snapshot_date):
    """Compute and upsert UserMetric rows for all active users on snapshot_date."""
    # Collect every user who had any activity on this date.
    created_qs = Task.objects.filter(
        created_at__date=snapshot_date, deleted_at__isnull=True
    ).values_list("created_by_id", "project_id")

    completed_qs = Task.objects.filter(
        completed_at__date=snapshot_date, deleted_at__isnull=True
    ).values_list("assigned_to_id", "project_id")

    comments_qs = Comment.objects.filter(
        created_at__date=snapshot_date, deleted_at__isnull=True
    ).values_list("author_id", "task__project_id")

    logs_qs = TimeLog.objects.filter(logged_date=snapshot_date).values_list(
        "user_id", "task__project_id"
    )

    # Build a set of (user_id, project_id) pairs that had activity.
    pairs: set[tuple] = set()
    for uid, pid in created_qs:
        if uid and pid:
            pairs.add((uid, pid))
    for uid, pid in completed_qs:
        if uid and pid:
            pairs.add((uid, pid))
    for uid, pid in comments_qs:
        if uid and pid:
            pairs.add((uid, pid))
    for uid, pid in logs_qs:
        if uid and pid:
            pairs.add((uid, pid))

    for user_id, project_id in pairs:
        tasks_created = Task.objects.filter(
            created_by_id=user_id,
            project_id=project_id,
            created_at__date=snapshot_date,
            deleted_at__isnull=True,
        ).count()

        tasks_completed = Task.objects.filter(
            assigned_to_id=user_id,
            project_id=project_id,
            completed_at__date=snapshot_date,
            deleted_at__isnull=True,
        ).count()

        comments_posted = Comment.objects.filter(
            author_id=user_id,
            task__project_id=project_id,
            created_at__date=snapshot_date,
            deleted_at__isnull=True,
        ).count()

        logged_minutes = (
            TimeLog.objects.filter(
                user_id=user_id,
                task__project_id=project_id,
                logged_date=snapshot_date,
            ).aggregate(total=Sum("logged_minutes"))["total"] or 0
        )

        UserMetric.objects.update_or_create(
            user_id=user_id,
            project_id=project_id,
            metric_date=snapshot_date,
            defaults={
                "tasks_created": tasks_created,
                "tasks_completed": tasks_completed,
                "tasks_assigned": 0,  # tracked via assignment events in a future release
                "comments_posted": comments_posted,
                "logged_minutes": logged_minutes,
            },
        )


class Command(BaseCommand):
    help = "Generate TaskSnapshot and UserMetric rows. Use --since for backfill."

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            type=str,
            default=None,
            help="Start date for backfill (YYYY-MM-DD). Defaults to today only.",
        )

    def handle(self, *args, **options):
        since_str = options["since"]

        if since_str:
            try:
                start = date.fromisoformat(since_str)
            except ValueError:
                raise CommandError(f"Invalid date format: {since_str!r}. Use YYYY-MM-DD.")
            dates = list(_date_range(start, date.today()))
        else:
            dates = [date.today()]

        projects = list(Project.objects.filter(status=ProjectStatus.ACTIVE))
        self.stdout.write(
            f"Generating snapshots for {len(dates)} date(s) across {len(projects)} project(s)…"
        )

        for snapshot_date in dates:
            for project in projects:
                # Project-level snapshot (no sprint filter)
                _snapshot_for(project, None, snapshot_date)

                # Per-sprint snapshots (active + completed)
                sprints = Sprint.objects.filter(project=project).exclude(
                    status=SprintStatus.PLANNED
                )
                for sprint in sprints:
                    _snapshot_for(project, sprint, snapshot_date)

            _user_metrics_for(snapshot_date)
            self.stdout.write(f"  ✓ {snapshot_date}")

        self.stdout.write(self.style.SUCCESS("Done."))
