from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.models import Project, ProjectMember, ProjectRole, Sprint, SprintStatus
from tasks.models import Task
from users.models import User

from .models import TaskSnapshot, UserMetric
from .serializers import TaskSnapshotSerializer, UserMetricSerializer


def _can_view_project(user, project):
    if user.has_elevated_access():
        return True
    return ProjectMember.objects.filter(project=project, user=user).exists()


def _can_view_analytics(user, project):
    """PO/PM or elevated access required for per-member metrics."""
    if user.has_elevated_access():
        return True
    membership = ProjectMember.objects.filter(project=project, user=user).first()
    return membership and membership.role in (ProjectRole.PO, ProjectRole.PM)


def _can_view_summary(user, project):
    """PO/PM/DEV or elevated access required for project summary analytics."""
    if user.has_elevated_access():
        return True
    membership = ProjectMember.objects.filter(project=project, user=user).first()
    return membership and membership.role in (ProjectRole.PO, ProjectRole.PM, ProjectRole.DEV)


def _velocity(project):
    """Average completed story points across the last 3 completed sprints."""
    sprints = (
        Sprint.objects.filter(project=project, status=SprintStatus.COMPLETED)
        .order_by("-completed_at")[:3]
    )
    if not sprints:
        return 0.0
    totals = [
        Task.objects.filter(
            sprint=s, status="done", deleted_at__isnull=True
        ).aggregate(sp=Sum("story_points"))["sp"] or 0
        for s in sprints
    ]
    return round(sum(totals) / len(totals), 1)


# ---------------------------------------------------------------------------
# Snapshot (burndown data)
# ---------------------------------------------------------------------------

class ProjectSnapshotListView(APIView):
    """GET /api/projects/<pk>/snapshots/"""

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        if not _can_view_project(request.user, project):
            return Response({"detail": "Not found."}, status=404)

        qs = TaskSnapshot.objects.filter(project=project)

        sprint_id = request.query_params.get("sprint_id")
        if sprint_id:
            qs = qs.filter(sprint_id=sprint_id)
        else:
            qs = qs.filter(sprint__isnull=True)

        if since := request.query_params.get("since"):
            qs = qs.filter(snapshot_date__gte=since)
        if until := request.query_params.get("until"):
            qs = qs.filter(snapshot_date__lte=until)

        return Response(TaskSnapshotSerializer(qs, many=True).data)


# ---------------------------------------------------------------------------
# Project summary (realtime)
# ---------------------------------------------------------------------------

class ProjectMetricsSummaryView(APIView):
    """GET /api/projects/<pk>/metrics/summary/"""

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        if not _can_view_summary(request.user, project):
            return Response({"detail": "Not found."}, status=404)

        now = timezone.now()
        tasks = Task.objects.filter(project=project, deleted_at__isnull=True)

        total = tasks.count()
        open_count = tasks.exclude(status__in=["done", "cancelled"]).count()
        completed = tasks.filter(status="done").count()
        overdue = tasks.filter(due_date__lt=now).exclude(
            status__in=["done", "cancelled"]
        ).count()

        agg = tasks.aggregate(
            total_sp=Sum("story_points"),
            completed_sp=Sum("story_points", filter=Q(status="done")),
        )

        active_sprint = Sprint.objects.filter(
            project=project, status=SprintStatus.ACTIVE
        ).first()

        return Response({
            "total_tasks": total,
            "open_tasks": open_count,
            "completed_tasks": completed,
            "overdue_tasks": overdue,
            "total_story_points": agg["total_sp"] or 0,
            "completed_story_points": agg["completed_sp"] or 0,
            "velocity": _velocity(project),
            "progress": round(completed / total * 100) if total > 0 else 0,
            "active_sprint": {
                "id": str(active_sprint.pk),
                "name": active_sprint.name,
                "status": active_sprint.status,
            } if active_sprint else None,
        })


# ---------------------------------------------------------------------------
# Per-member metrics (role-gated)
# ---------------------------------------------------------------------------

class ProjectMemberMetricsView(APIView):
    """GET /api/projects/<pk>/metrics/users/"""

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        if not _can_view_analytics(request.user, project):
            return Response({"detail": "Forbidden."}, status=403)

        qs = UserMetric.objects.filter(project=project).select_related("user")

        if since := request.query_params.get("since"):
            qs = qs.filter(metric_date__gte=since)
        if until := request.query_params.get("until"):
            qs = qs.filter(metric_date__lte=until)

        aggregated = (
            qs.values("user__id", "user__display_name", "user__email")
            .annotate(
                total_created=Sum("tasks_created"),
                total_completed=Sum("tasks_completed"),
                total_assigned=Sum("tasks_assigned"),
                total_comments=Sum("comments_posted"),
                total_minutes=Sum("logged_minutes"),
            )
        )

        return Response([
            {
                "user": {
                    "id": str(row["user__id"]),
                    "display_name": row["user__display_name"],
                    "email": row["user__email"],
                },
                "tasks_created": row["total_created"] or 0,
                "tasks_completed": row["total_completed"] or 0,
                "tasks_assigned": row["total_assigned"] or 0,
                "comments_posted": row["total_comments"] or 0,
                "logged_minutes": row["total_minutes"] or 0,
            }
            for row in aggregated
        ])


# ---------------------------------------------------------------------------
# Personal metrics
# ---------------------------------------------------------------------------

class UserMetricsView(APIView):
    """GET /api/users/<pk>/metrics/"""

    def get(self, request, pk):
        if str(request.user.pk) != str(pk) and not request.user.has_elevated_access():
            return Response({"detail": "Forbidden."}, status=403)

        user = get_object_or_404(User, pk=pk)
        qs = UserMetric.objects.filter(user=user)

        if project_id := request.query_params.get("project_id"):
            qs = qs.filter(project_id=project_id)
        if since := request.query_params.get("since"):
            qs = qs.filter(metric_date__gte=since)
        if until := request.query_params.get("until"):
            qs = qs.filter(metric_date__lte=until)

        return Response(UserMetricSerializer(qs, many=True).data)
