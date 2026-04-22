from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone as tz
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.models import Label, Project, ProjectMember, ProjectRole, ProjectStatus, ProjectType, Sprint, SprintStatus, TaskStatus
from users.models import User

from .models import ActivityLog, Comment, Task, TaskDependency, TaskGuestAccess
from .serializers import (
    ActivityLogSerializer,
    CommentCreateSerializer,
    CommentSerializer,
    CommentUpdateSerializer,
    ProjectTaskCreateSerializer,
    ReactionSerializer,
    TaskAssignmentAddSerializer,
    TaskAssignmentSerializer,
    TaskCreateSerializer,
    TaskDependencyCreateSerializer,
    TaskDependencySerializer,
    TaskGuestAccessCreateSerializer,
    TaskGuestAccessSerializer,
    TaskLabelAddSerializer,
    TaskLabelSerializer,
    TaskSearchResultSerializer,
    TaskSerializer,
    TaskUpdateSerializer,
    TimeLogCreateSerializer,
    TimeLogSerializer,
    TimeLogUpdateSerializer,
)
from .services import AccessControlService, AttachmentService, CommentService, TaskService

_VALID_SORT_FIELDS = {"created_at", "due_date", "priority", "position"}


def _can_manage_guest_access(user, task):
    if user.has_elevated_access():
        return True
    membership = ProjectMember.objects.filter(project=task.project, user=user).first()
    return membership and membership.role in (ProjectRole.PO, ProjectRole.PM)


def _get_or_create_personal_project(user):
    """
    Returns the user's personal project, creating it if it doesn't exist.
    Uses select_for_update to guard against concurrent first-write races.
    """
    from django.db import IntegrityError, transaction
    from projects.models import Workspace
    from projects.services import WorkspaceService

    with transaction.atomic():
        personal_ws = (
            Workspace.objects.select_for_update()
            .filter(owner=user, is_personal=True)
            .first()
        )
        if not personal_ws:
            personal_ws = WorkspaceService.create_personal_workspace(user)

        try:
            project, created = Project.objects.get_or_create(
                workspace=personal_ws,
                type=ProjectType.PERSONAL,
                defaults={
                    "name": "Personal",
                    "key": "PERS",
                    "status": ProjectStatus.ACTIVE,
                    "created_by": user,
                },
            )
        except IntegrityError:
            project = Project.objects.get(workspace=personal_ws, type=ProjectType.PERSONAL)
            created = False

        if created:
            ProjectMember.objects.create(project=project, user=user, role=ProjectRole.PO)

    return project


class TaskListCreateView(APIView):
    """
    GET  /api/tasks/?project_id=<uuid>  — list tasks in a project
    POST /api/tasks/                    — create a new task
    """

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return Response({"detail": "project_id query parameter is required."}, status=400)

        project = get_object_or_404(Project, pk=project_id)

        if not request.user.has_elevated_access():
            membership = ProjectMember.objects.filter(
                project=project, user=request.user
            ).first()
            if not membership:
                return Response(
                    {"detail": "You are not a member of this project."}, status=403
                )

        tasks = (
            Task.objects.filter(project=project, deleted_at__isnull=True)
            .select_related("created_by", "assigned_to")
            .prefetch_related("task_labels__label")
            .order_by("position", "created_at")
        )

        # Guests see only public tasks
        if not request.user.has_elevated_access():
            membership = ProjectMember.objects.filter(
                project=project, user=request.user
            ).first()
            if membership and membership.role == ProjectRole.GU:
                tasks = tasks.filter(is_private=False)

        status = request.query_params.get("status")
        if status:
            tasks = tasks.filter(status=status)

        assigned_to = request.query_params.get("assigned_to")
        if assigned_to:
            tasks = tasks.filter(assigned_to_id=assigned_to)

        priority = request.query_params.get("priority")
        if priority:
            tasks = tasks.filter(priority=priority)

        task_type = request.query_params.get("type")
        if task_type:
            tasks = tasks.filter(type=task_type)

        return Response(TaskSerializer(tasks, many=True).data)

    def post(self, request):
        # Resolve project: use the provided project_id or fall back to the user's personal project.
        project_id = request.data.get("project_id")
        if project_id:
            try:
                project = Project.objects.get(pk=project_id, status=ProjectStatus.ACTIVE)
            except (Project.DoesNotExist, ValueError):
                return Response({"detail": "Project not found."}, status=400)
            if not request.user.has_elevated_access():
                if not ProjectMember.objects.filter(project=project, user=request.user).exists():
                    return Response({"detail": "You are not a member of this project."}, status=403)
        else:
            project = _get_or_create_personal_project(request.user)

        # Always pass the resolved project_id to the serializer so validation works normally.
        data = {**request.data, "project_id": str(project.id)}
        serializer = TaskCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        try:
            task = serializer.save(creator=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(TaskSerializer(task).data, status=201)


class ProjectTaskListCreateView(APIView):
    """
    GET  /api/projects/<uuid>/tasks/ — list tasks in a project
    POST /api/projects/<uuid>/tasks/ — create a new task
    """

    def _get_membership(self, request, project):
        if request.user.has_elevated_access():
            return True, None
        membership = ProjectMember.objects.filter(project=project, user=request.user).first()
        if not membership:
            return False, None
        return True, membership

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        allowed, membership = self._get_membership(request, project)
        if not allowed:
            return Response({"detail": "Not found."}, status=404)

        tasks = (
            Task.objects.filter(project=project, deleted_at__isnull=True)
            .select_related("created_by", "assigned_to")
            .prefetch_related("task_labels__label")
            .order_by("position", "created_at")
        )

        if membership and membership.role == ProjectRole.GU:
            tasks = tasks.filter(is_private=False)

        status = request.query_params.get("status")
        if status:
            tasks = tasks.filter(status__in=[s.strip() for s in status.split(",")])

        priority = request.query_params.get("priority")
        if priority:
            tasks = tasks.filter(priority__in=[p.strip() for p in priority.split(",")])

        task_type = request.query_params.get("type")
        if task_type:
            tasks = tasks.filter(type__in=[t.strip() for t in task_type.split(",")])

        assigned_to = request.query_params.get("assigned_to")
        if assigned_to:
            tasks = tasks.filter(assigned_to_id=assigned_to)

        sprint_id = request.query_params.get("sprint_id")
        if sprint_id:
            tasks = tasks.filter(sprint_id=sprint_id)

        label_ids = request.query_params.get("label_ids")
        if label_ids:
            ids = [i.strip() for i in label_ids.split(",")]
            tasks = tasks.filter(task_labels__label_id__in=ids).distinct()

        due_before = request.query_params.get("due_before")
        if due_before:
            tasks = tasks.filter(due_date__date__lte=due_before)

        due_after = request.query_params.get("due_after")
        if due_after:
            tasks = tasks.filter(due_date__date__gte=due_after)

        search = request.query_params.get("search")
        if search:
            tasks = tasks.filter(title__icontains=search)

        parent_task_id = request.query_params.get("parent_task_id")
        if parent_task_id == "null":
            tasks = tasks.filter(parent_task__isnull=True)
        elif parent_task_id:
            tasks = tasks.filter(parent_task_id=parent_task_id)

        sort_by = request.query_params.get("sort_by", "position")
        sort_dir = request.query_params.get("sort_dir", "asc")
        if sort_by not in _VALID_SORT_FIELDS:
            sort_by = "position"
        order_field = f"-{sort_by}" if sort_dir == "desc" else sort_by
        tasks = tasks.order_by(order_field, "created_at")

        return Response(TaskSerializer(tasks, many=True).data)

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)

        if not request.user.has_elevated_access():
            membership = ProjectMember.objects.filter(project=project, user=request.user).first()
            if not membership:
                return Response({"detail": "Not found."}, status=404)
            if membership.role in (ProjectRole.VW, ProjectRole.GU):
                return Response({"detail": "You do not have permission to create tasks."}, status=403)

        serializer = ProjectTaskCreateSerializer(
            data=request.data, context={"request": request, "project": project}
        )
        serializer.is_valid(raise_exception=True)
        try:
            task = serializer.save(creator=request.user, project=project)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(TaskSerializer(task).data, status=201)


class TaskDetailView(APIView):
    """
    GET    /api/tasks/<uuid>/  — retrieve a task
    PATCH  /api/tasks/<uuid>/  — partially update a task
    DELETE /api/tasks/<uuid>/  — soft-delete a task
    """

    def _get_task(self, pk):
        return get_object_or_404(Task, pk=pk)

    def get(self, request, pk):
        task = self._get_task(pk)
        if not AccessControlService.can_view_task(request.user, task):
            return Response({"detail": "Not found."}, status=404)
        return Response(TaskSerializer(task).data)

    def patch(self, request, pk):
        task = self._get_task(pk)
        if not AccessControlService.can_edit_task(request.user, task):
            return Response(
                {"detail": "You do not have permission to edit this task."}, status=403
            )
        serializer = TaskUpdateSerializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            task = serializer.save(actor=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(TaskSerializer(task).data)

    def delete(self, request, pk):
        task = self._get_task(pk)
        if not AccessControlService.can_edit_task(request.user, task):
            return Response(
                {"detail": "You do not have permission to delete this task."}, status=403
            )
        try:
            TaskService.soft_delete(task, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(status=204)


class TaskSubtaskListView(APIView):
    """
    GET /api/tasks/<uuid>/subtasks/ — list subtasks of a task
    """

    def get(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        if not AccessControlService.can_view_task(request.user, task):
            return Response({"detail": "Not found."}, status=404)

        subtasks = (
            Task.objects.filter(parent_task=task, deleted_at__isnull=True)
            .select_related("created_by", "assigned_to")
            .order_by("position", "created_at")
        )

        status = request.query_params.get("status")
        if status:
            subtasks = subtasks.filter(status=status)

        return Response(TaskSerializer(subtasks, many=True).data)


class TaskAssignmentListView(APIView):
    """
    GET  /api/tasks/<uuid>/assignments/ — list co-assignees
    POST /api/tasks/<uuid>/assignments/ — add a co-assignee
    """

    def get(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        if not AccessControlService.can_view_task(request.user, task):
            return Response({"detail": "Not found."}, status=404)
        assignments = task.co_assignments.select_related("user", "assigned_by")
        return Response(TaskAssignmentSerializer(assignments, many=True).data)

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        if not AccessControlService.can_edit_task(request.user, task):
            return Response({"detail": "Permission denied."}, status=403)

        serializer = TaskAssignmentAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user_id"]
        assignment = TaskService.add_co_assignee(task, user, request.user)
        return Response(TaskAssignmentSerializer(assignment).data, status=201)


class TaskAssignmentDetailView(APIView):
    """
    DELETE /api/tasks/<uuid>/assignments/<user_id>/ — remove a co-assignee
    """

    def delete(self, request, pk, user_id):
        task = get_object_or_404(Task, pk=pk)
        if not AccessControlService.can_edit_task(request.user, task):
            return Response({"detail": "Permission denied."}, status=403)
        user = get_object_or_404(User, pk=user_id)
        TaskService.remove_co_assignee(task, user)
        return Response(status=204)


class TaskLabelListView(APIView):
    """
    GET  /api/tasks/<uuid>/labels/ — list labels on a task
    POST /api/tasks/<uuid>/labels/ — attach a label to a task
    """

    def get(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        if not AccessControlService.can_view_task(request.user, task):
            return Response({"detail": "Not found."}, status=404)
        labels = task.task_labels.select_related("label")
        return Response(TaskLabelSerializer(labels, many=True).data)

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        if not AccessControlService.can_edit_task(request.user, task):
            return Response({"detail": "Permission denied."}, status=403)

        serializer = TaskLabelAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        label = serializer.validated_data["label_id"]
        TaskService.add_label(task, label)
        return Response(status=201)


class TaskLabelDetailView(APIView):
    """
    DELETE /api/tasks/<uuid>/labels/<label_id>/ — detach a label from a task
    """

    def delete(self, request, pk, label_id):
        task = get_object_or_404(Task, pk=pk)
        if not AccessControlService.can_edit_task(request.user, task):
            return Response({"detail": "Permission denied."}, status=403)
        label = get_object_or_404(Label, pk=label_id)
        TaskService.remove_label(task, label)
        return Response(status=204)


class TaskDependencyListView(APIView):
    """
    GET  /api/tasks/<uuid>/dependencies/ — list dependencies
    POST /api/tasks/<uuid>/dependencies/ — add a dependency
    """

    def get(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        if not AccessControlService.can_view_task(request.user, task):
            return Response({"detail": "Not found."}, status=404)
        deps = task.dependencies.select_related("depends_on_task", "created_by")
        return Response(TaskDependencySerializer(deps, many=True).data)

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        if not AccessControlService.can_edit_task(request.user, task):
            return Response({"detail": "Permission denied."}, status=403)

        serializer = TaskDependencyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        depends_on = serializer.validated_data["depends_on_task_id"]
        dep_type = serializer.validated_data["type"]
        try:
            dep = TaskService.add_dependency(task, depends_on, dep_type, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(TaskDependencySerializer(dep).data, status=201)


class TaskDependencyDetailView(APIView):
    """
    PATCH  /api/tasks/<uuid>/dependencies/<dep_id>/ — update dependency type
    DELETE /api/tasks/<uuid>/dependencies/<dep_id>/ — remove a dependency
    """

    def patch(self, request, pk, dep_id):
        task = get_object_or_404(Task, pk=pk)
        if not AccessControlService.can_edit_task(request.user, task):
            return Response({"detail": "Permission denied."}, status=403)
        dep = get_object_or_404(TaskDependency, pk=dep_id, task=task)
        new_type = request.data.get("type")
        if not new_type or new_type not in dict(TaskDependency._meta.get_field("type").choices if hasattr(TaskDependency._meta.get_field("type"), "choices") else []):
            from .models import DependencyType
            valid = [c[0] for c in DependencyType.choices]
            if new_type not in valid:
                return Response({"detail": f"type must be one of: {valid}"}, status=400)
        dep.type = new_type
        dep.save(update_fields=["type"])
        return Response(TaskDependencySerializer(dep).data)

    def delete(self, request, pk, dep_id):
        task = get_object_or_404(Task, pk=pk)
        if not AccessControlService.can_edit_task(request.user, task):
            return Response({"detail": "Permission denied."}, status=403)
        dep = get_object_or_404(TaskDependency, pk=dep_id, task=task)
        dep.delete()
        return Response(status=204)


class TaskGuestAccessListView(APIView):
    """
    GET  /api/tasks/<uuid>/guest-access/ — list users with guest access
    POST /api/tasks/<uuid>/guest-access/ — grant guest access
    """

    def get(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        if not _can_manage_guest_access(request.user, task):
            return Response({"detail": "Permission denied."}, status=403)
        accesses = task.guest_accesses.select_related("user", "granted_by")
        return Response(TaskGuestAccessSerializer(accesses, many=True).data)

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        if not _can_manage_guest_access(request.user, task):
            return Response({"detail": "Permission denied."}, status=403)

        serializer = TaskGuestAccessCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user_id"]
        expires_at = serializer.validated_data.get("expires_at")
        access = TaskService.grant_guest_access(task, user, request.user)
        if expires_at is not None:
            access.expires_at = expires_at
            access.save(update_fields=["expires_at"])
        return Response(TaskGuestAccessSerializer(access).data, status=201)


class TaskGuestAccessDetailView(APIView):
    """
    DELETE /api/tasks/<uuid>/guest-access/<user_id>/ — revoke guest access
    """

    def delete(self, request, pk, user_id):
        task = get_object_or_404(Task, pk=pk)
        if not _can_manage_guest_access(request.user, task):
            return Response({"detail": "Permission denied."}, status=403)
        TaskGuestAccess.objects.filter(task=task, user_id=user_id).delete()
        return Response(status=204)


def _get_monday_of_week(dt):
    """Returns midnight UTC on Monday of the week containing dt."""
    import datetime as _dt
    dt_utc = dt.astimezone(_dt.timezone.utc)
    days_since_monday = dt_utc.weekday()
    return (dt_utc - timedelta(days=days_since_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


class DashboardStatsView(APIView):
    """
    GET /api/dashboard/stats/

    Returns aggregated task statistics for the authenticated user.
    """

    def get(self, request):
        from projects.request_helpers import _active_ws
        active_ws = _active_ws(request)
        user = request.user
        now = tz.now()
        active_ws = get_active_workspace(request)

        open_statuses = [
            TaskStatus.BACKLOG,
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
            TaskStatus.IN_REVIEW,
        ]

        ws_filter = {"project__workspace": active_ws} if active_ws else {}
        base_qs = Task.objects.filter(
            assigned_to=user,
            deleted_at__isnull=True,
            **ws_filter,
        )
        if active_ws is not None:
            base_qs = base_qs.filter(project__workspace=active_ws)

        yesterday = now - timedelta(days=1)
        monday_this_week = _get_monday_of_week(now)
        monday_last_week = monday_this_week - timedelta(weeks=1)

        # Collapse all counts into one DB round-trip using conditional aggregation
        stats = base_qs.aggregate(
            open_tasks=Count(
                "id", filter=Q(status__in=open_statuses)
            ),
            open_tasks_delta=Count(
                "id", filter=Q(status__in=open_statuses, created_at__gte=yesterday)
            ),
            done_this_week=Count(
                "id", filter=Q(status=TaskStatus.DONE, completed_at__gte=monday_this_week)
            ),
            done_last_week=Count(
                "id",
                filter=Q(
                    status=TaskStatus.DONE,
                    completed_at__gte=monday_last_week,
                    completed_at__lt=monday_this_week,
                ),
            ),
            overdue=Count(
                "id", filter=Q(status__in=open_statuses, due_date__lt=now)
            ),
        )

        open_tasks = stats["open_tasks"]
        open_tasks_delta = stats["open_tasks_delta"]
        done_this_week = stats["done_this_week"]
        done_last_week = stats["done_last_week"]
        overdue = stats["overdue"]

        if done_last_week > 0:
            done_this_week_delta_pct = round((done_this_week / done_last_week - 1) * 100)
        else:
            done_this_week_delta_pct = 0

        overdue = base_qs.filter(
            status__in=open_statuses,
            due_date__lt=now,
        ).count()

        pm_qs = ProjectMember.objects.filter(user=user)
        if active_ws is not None:
            pm_qs = pm_qs.filter(project__workspace=active_ws)
        user_project_ids = pm_qs.values_list("project_id", flat=True)
        active_sprint = (
            Sprint.objects.filter(
                project_id__in=user_project_ids,
                status=SprintStatus.ACTIVE,
            )
            .order_by("-start_date")
            .first()
        )

        story_points = 0
        story_points_total = 0
        if active_sprint:
            sprint_tasks = Task.objects.filter(
                sprint=active_sprint,
                deleted_at__isnull=True,
            )
            story_points = sprint_tasks.filter(status=TaskStatus.DONE).aggregate(
                total=Sum("story_points")
            )["total"] or 0
            story_points_total = sprint_tasks.aggregate(
                total=Sum("story_points")
            )["total"] or 0

        return Response({
            "open_tasks": open_tasks,
            "open_tasks_delta": open_tasks_delta,
            "done_this_week": done_this_week,
            "done_this_week_delta_pct": done_this_week_delta_pct,
            "story_points": story_points,
            "story_points_total": story_points_total,
            "overdue": overdue,
        })


# ---------------------------------------------------------------------------
# Comment views
# ---------------------------------------------------------------------------

class TaskCommentListView(APIView):
    """
    GET  /api/tasks/<pk>/comments/  — list non-deleted comments
    POST /api/tasks/<pk>/comments/  — add a comment
    """

    def _get_task(self, pk, user):
        task = get_object_or_404(Task, pk=pk, deleted_at__isnull=True)
        if not AccessControlService.can_view_task(user, task):
            return None
        return task

    def get(self, request, pk):
        task = self._get_task(pk, request.user)
        if not task:
            return Response({"detail": "Not found."}, status=404)
        comments = (
            Comment.objects.filter(task=task, deleted_at__isnull=True)
            .select_related("author")
            .order_by("created_at")
        )
        return Response(CommentSerializer(comments, many=True).data)

    def post(self, request, pk):
        task = self._get_task(pk, request.user)
        if not task:
            return Response({"detail": "Not found."}, status=404)
        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        parent = None
        if data.get("parent_comment_id"):
            parent = get_object_or_404(
                Comment, pk=data["parent_comment_id"], task=task, deleted_at__isnull=True
            )

        comment = CommentService.add_comment(
            task=task,
            author=request.user,
            body=data["body"],
            parent_comment=parent,
        )
        comment = Comment.objects.select_related("author").get(pk=comment.pk)
        return Response(CommentSerializer(comment).data, status=201)


class CommentDetailView(APIView):
    """
    GET    /api/comments/<pk>/  — fetch a single comment
    PATCH  /api/comments/<pk>/  — edit comment (author or SA)
    DELETE /api/comments/<pk>/  — soft-delete (author, PM, PO, or SA)
    """

    def _get_comment(self, pk):
        return get_object_or_404(Comment, pk=pk, deleted_at__isnull=True)

    def get(self, request, pk):
        from .serializers import CommentSerializer
        comment = self._get_comment(pk)
        if not AccessControlService.can_view_task(request.user, comment.task):
            return Response({"detail": "Not found."}, status=404)
        comment = Comment.objects.select_related("author").prefetch_related("reactions").get(pk=pk)
        return Response(CommentSerializer(comment).data)

    def patch(self, request, pk):
        comment = self._get_comment(pk)
        is_author = comment.author_id == request.user.pk
        is_sa = request.user.global_role == "SA"
        if not is_author and not is_sa:
            return Response({"detail": "Only the author or SA can edit this comment."}, status=403)
        serializer = CommentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = CommentService.edit_comment(comment, request.user, serializer.validated_data["body"])
        comment = Comment.objects.select_related("author").get(pk=comment.pk)
        return Response(CommentSerializer(comment).data)

    def delete(self, request, pk):
        comment = self._get_comment(pk)
        is_author = comment.author_id == request.user.pk
        is_elevated = request.user.has_elevated_access()
        membership = ProjectMember.objects.filter(
            project=comment.task.project, user=request.user
        ).first()
        is_pm_or_po = membership and membership.role in (ProjectRole.PO, ProjectRole.PM)
        if not is_author and not is_elevated and not is_pm_or_po:
            return Response({"detail": "Insufficient permissions."}, status=403)
        CommentService.soft_delete_comment(comment, request.user)
        return Response(status=204)


# ---------------------------------------------------------------------------
# Activity views
# ---------------------------------------------------------------------------

class ProjectActivityView(APIView):
    """
    GET /api/projects/<pk>/activity/  — project activity feed
    """

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        if not request.user.has_elevated_access():
            if not ProjectMember.objects.filter(project=project, user=request.user).exists():
                return Response({"detail": "Not found."}, status=404)

        qs = (
            ActivityLog.objects.filter(project=project)
            .select_related("actor")
            .order_by("-created_at")
        )
        if entity_type := request.query_params.get("entity_type"):
            qs = qs.filter(entity_type=entity_type)
        if actor_id := request.query_params.get("actor_id"):
            qs = qs.filter(actor_id=actor_id)
        if action := request.query_params.get("action"):
            qs = qs.filter(action=action)
        if since := request.query_params.get("since"):
            qs = qs.filter(created_at__gte=since)
        if until := request.query_params.get("until"):
            qs = qs.filter(created_at__lte=until)

        limit = min(int(request.query_params.get("limit", 50)), 100)
        return Response(ActivityLogSerializer(qs[:limit], many=True).data)


class TaskActivityView(APIView):
    """
    GET /api/tasks/<pk>/activity/  — task activity feed
    """

    def get(self, request, pk):
        task = get_object_or_404(Task, pk=pk, deleted_at__isnull=True)
        if not AccessControlService.can_view_task(request.user, task):
            return Response({"detail": "Not found."}, status=404)
        qs = (
            ActivityLog.objects.filter(entity_type="task", entity_id=task.pk)
            .select_related("actor")
            .order_by("-created_at")
        )
        limit = min(int(request.query_params.get("limit", 50)), 100)
        return Response(ActivityLogSerializer(qs[:limit], many=True).data)


# ---------------------------------------------------------------------------
# Custom field views
# ---------------------------------------------------------------------------

class ProjectCustomFieldListView(APIView):
    """
    GET  /api/projects/<pk>/custom-fields/  — list fields
    POST /api/projects/<pk>/custom-fields/  — create field (PO/PM/SA/GA)
    """

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        if not request.user.has_elevated_access():
            if not ProjectMember.objects.filter(project=project, user=request.user).exists():
                return Response({"detail": "Not found."}, status=404)
        from tasks.models import CustomField
        from tasks.serializers import CustomFieldSerializer
        fields = CustomField.objects.filter(project=project).select_related("created_by").order_by("position")
        return Response(CustomFieldSerializer(fields, many=True).data)

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        if not request.user.has_elevated_access():
            m = ProjectMember.objects.filter(project=project, user=request.user).first()
            if not m or m.role not in (ProjectRole.PO, ProjectRole.PM):
                return Response({"detail": "Insufficient permissions."}, status=403)
        from tasks.models import CustomField
        from tasks.serializers import CustomFieldCreateSerializer, CustomFieldSerializer
        serializer = CustomFieldCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        field = CustomField.objects.create(project=project, created_by=request.user, **data)
        field = CustomField.objects.select_related("created_by").get(pk=field.pk)
        return Response(CustomFieldSerializer(field).data, status=201)


class ProjectCustomFieldDetailView(APIView):
    """
    PATCH  /api/projects/<pk>/custom-fields/<field_id>/
    DELETE /api/projects/<pk>/custom-fields/<field_id>/
    """

    def _get_field(self, pk, field_id):
        project = get_object_or_404(Project, pk=pk)
        from tasks.models import CustomField
        return project, get_object_or_404(CustomField, pk=field_id, project=project)

    def _check_manage_perm(self, user, project):
        if user.has_elevated_access():
            return True
        m = ProjectMember.objects.filter(project=project, user=user).first()
        return m and m.role in (ProjectRole.PO, ProjectRole.PM)

    def patch(self, request, pk, field_id):
        project, field = self._get_field(pk, field_id)
        if not self._check_manage_perm(request.user, project):
            return Response({"detail": "Insufficient permissions."}, status=403)
        from tasks.serializers import CustomFieldSerializer, CustomFieldUpdateSerializer
        serializer = CustomFieldUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for attr, value in serializer.validated_data.items():
            setattr(field, attr, value)
        field.save()
        from tasks.models import CustomField
        field = CustomField.objects.select_related("created_by").get(pk=field.pk)
        return Response(CustomFieldSerializer(field).data)

    def delete(self, request, pk, field_id):
        project, field = self._get_field(pk, field_id)
        if not (request.user.global_role == "SA" or (
            ProjectMember.objects.filter(project=project, user=request.user, role=ProjectRole.PO).exists()
        )):
            return Response({"detail": "Only PO or SA can delete custom fields."}, status=403)
        field.delete()
        return Response(status=204)


class TaskCustomFieldValueListView(APIView):
    """
    GET /api/tasks/<pk>/custom-field-values/  — list all values for task
    """

    def get(self, request, pk):
        task = get_object_or_404(Task, pk=pk, deleted_at__isnull=True)
        if not AccessControlService.can_view_task(request.user, task):
            return Response({"detail": "Not found."}, status=404)
        from tasks.models import TaskCustomFieldValue
        from tasks.serializers import TaskCustomFieldValueSerializer
        values = (
            TaskCustomFieldValue.objects.filter(task=task)
            .select_related("custom_field")
        )
        return Response(TaskCustomFieldValueSerializer(values, many=True).data)


class TaskCustomFieldValueDetailView(APIView):
    """
    PUT /api/tasks/<pk>/custom-field-values/<field_id>/  — set value
    """

    def put(self, request, pk, field_id):
        task = get_object_or_404(Task, pk=pk, deleted_at__isnull=True)
        if not AccessControlService.can_edit_task(request.user, task):
            return Response({"detail": "Insufficient permissions."}, status=403)
        from tasks.models import CustomField, TaskCustomFieldValue
        from tasks.serializers import TaskCustomFieldValueSerializer, TaskCustomFieldValueSetSerializer
        field = get_object_or_404(CustomField, pk=field_id, project=task.project)
        serializer = TaskCustomFieldValueSetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        value_obj, _ = TaskCustomFieldValue.objects.update_or_create(
            task=task, custom_field=field,
            defaults={"value": serializer.validated_data["value"]},
        )
        value_obj = TaskCustomFieldValue.objects.select_related("custom_field").get(pk=value_obj.pk)
        return Response(TaskCustomFieldValueSerializer(value_obj).data)

    def delete(self, request, pk, field_id):
        task = get_object_or_404(Task, pk=pk, deleted_at__isnull=True)
        if not AccessControlService.can_edit_task(request.user, task):
            return Response({"detail": "Insufficient permissions."}, status=403)
        from tasks.models import CustomField, TaskCustomFieldValue
        field = get_object_or_404(CustomField, pk=field_id, project=task.project)
        TaskCustomFieldValue.objects.filter(task=task, custom_field=field).delete()
        return Response(status=204)


# ---------------------------------------------------------------------------
# Reaction views
# ---------------------------------------------------------------------------

class CommentReactionView(APIView):
    """
    GET    /api/comments/<pk>/reactions/         — list reactions
    POST   /api/comments/<pk>/reactions/         — add reaction
    DELETE /api/comments/<pk>/reactions/<emoji>/ — remove reaction
    """

    def get(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk, deleted_at__isnull=True)
        from tasks.models import Reaction
        reactions = Reaction.objects.filter(comment=comment).select_related("user")
        return Response(ReactionSerializer(reactions, many=True).data)

    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk, deleted_at__isnull=True)
        emoji = request.data.get("emoji")
        if not emoji:
            return Response({"detail": "emoji is required."}, status=400)
        from tasks.models import Reaction
        reaction, created = Reaction.objects.get_or_create(comment=comment, user=request.user, emoji=emoji)
        return Response(ReactionSerializer(reaction).data, status=201 if created else 200)

    def delete(self, request, pk, emoji):
        comment = get_object_or_404(Comment, pk=pk, deleted_at__isnull=True)
        from tasks.models import Reaction
        Reaction.objects.filter(comment=comment, user=request.user, emoji=emoji).delete()
        return Response(status=204)


# ---------------------------------------------------------------------------
# Move-to-column / restore
# ---------------------------------------------------------------------------

class TaskMoveColumnView(APIView):
    """
    POST /api/tasks/<pk>/move-column/ — move task to a board column
    """

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk, deleted_at__isnull=True)
        if not AccessControlService.can_edit_task(request.user, task):
            return Response({"detail": "Permission denied."}, status=403)
        column_id = request.data.get("column_id")
        if not column_id:
            return Response({"detail": "column_id is required."}, status=400)
        from projects.models import BoardColumn
        column = get_object_or_404(BoardColumn, pk=column_id)
        try:
            task = TaskService.move_to_column(task, column, request.user)
        except ValueError as exc:
            msg = str(exc)
            status_code = 409 if "WIP limit" in msg else 400
            return Response({"detail": msg}, status=status_code)
        return Response(TaskSerializer(task).data)


class TaskRestoreView(APIView):
    """
    POST /api/tasks/<pk>/restore/ — restore a soft-deleted task
    """

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        if not AccessControlService.can_restore_task(request.user, task):
            return Response({"detail": "Permission denied."}, status=403)
        try:
            task = TaskService.restore(task, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(TaskSerializer(task).data)


# ---------------------------------------------------------------------------
# TimeLog views
# ---------------------------------------------------------------------------

class TaskTimeLogListView(APIView):
    """
    GET  /api/tasks/<pk>/time-logs/  — list time logs
    POST /api/tasks/<pk>/time-logs/  — create time log (min role: DEV)
    """

    def get(self, request, pk):
        task = get_object_or_404(Task, pk=pk, deleted_at__isnull=True)
        if not AccessControlService.can_view_task(request.user, task):
            return Response({"detail": "Not found."}, status=404)
        from tasks.models import TimeLog
        qs = TimeLog.objects.filter(task=task).select_related("user").order_by("-logged_date")
        since = request.query_params.get("since")
        if since:
            qs = qs.filter(logged_date__gte=since)
        until = request.query_params.get("until")
        if until:
            qs = qs.filter(logged_date__lte=until)
        total_minutes = qs.aggregate(total=Sum("logged_minutes"))["total"] or 0
        return Response({"data": TimeLogSerializer(qs, many=True).data, "meta": {"total_minutes": total_minutes}})

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk, deleted_at__isnull=True)
        if not AccessControlService.can_edit_task(request.user, task):
            return Response({"detail": "Insufficient permissions."}, status=403)
        serializer = TimeLogCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from tasks.models import TimeLog
        t = TimeLog.objects.create(
            task=task,
            user=request.user,
            **serializer.validated_data,
        )
        t_with_user = TimeLog.objects.select_related("user").get(pk=t.pk)
        return Response(TimeLogSerializer(t_with_user).data, status=201)


class TimeLogDetailView(APIView):
    """
    PATCH  /api/time-logs/<pk>/  — update time log (owner or SA)
    DELETE /api/time-logs/<pk>/  — delete time log (owner or SA)
    """

    def _get_log(self, pk, user):
        from tasks.models import TimeLog
        log = get_object_or_404(TimeLog, pk=pk)
        if log.user_id != user.pk and user.global_role != "SA":
            return None
        return log

    def patch(self, request, pk):
        log = self._get_log(pk, request.user)
        if not log:
            return Response({"detail": "Forbidden."}, status=403)
        serializer = TimeLogUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(log, field, value)
        log.save()
        from tasks.models import TimeLog
        log = TimeLog.objects.select_related("user").get(pk=log.pk)
        return Response(TimeLogSerializer(log).data)

    def delete(self, request, pk):
        log = self._get_log(pk, request.user)
        if not log:
            return Response({"detail": "Forbidden."}, status=403)
        log.delete()
        return Response(status=204)


# ---------------------------------------------------------------------------
# Home page: today tasks + user activity feed
# ---------------------------------------------------------------------------

def _due_label(due_date, now) -> str:
    today = now.date()
    due = due_date.date()
    delta = (due - today).days
    if delta == -1:
        return "Yesterday"
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Tomorrow"
    return f"{due.day} {due.strftime('%b')}"


class TodayTasksView(APIView):
    """
    GET /api/tasks/today/

    Returns tasks assigned to the authenticated user due within ±3 days,
    including overdue. Cancelled and deleted tasks are excluded.
    Scoped to the user's active workspace.
    """

    def get(self, request):
        from projects.request_helpers import _active_ws
        active_ws = _active_ws(request)
        now = tz.now()
        window_start = now - timedelta(days=2)
        window_end = now + timedelta(days=3)

        ws_filter = {"project__workspace": active_ws} if active_ws else {}

        tasks = (
            Task.objects.filter(
                assigned_to=request.user,
                deleted_at__isnull=True,
                due_date__range=(window_start, window_end),
                **ws_filter,
            )
            .exclude(status=TaskStatus.CANCELLED)
            .prefetch_related("task_labels__label")
            .order_by("due_date")
        )
        if active_ws is not None:
            tasks = tasks.filter(project__workspace=active_ws)

        result = []
        for task in tasks:
            first_label = task.task_labels.first()
            label_name = first_label.label.name if first_label else ""
            label_color = first_label.label.color if first_label else ""

            result.append({
                "id": str(task.id),
                "title": task.title,
                "label_name": label_name,
                "label_color": label_color,
                "due_label": _due_label(task.due_date, now),
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "done": task.status == TaskStatus.DONE,
            })

        return Response(result)


class UserActivityView(APIView):
    """
    GET /api/activity/

    Returns the last N activity log entries across all projects
    the authenticated user is a member of.
    """

    def get(self, request):
        user_project_ids = ProjectMember.objects.filter(
            user=request.user
        ).values_list("project_id", flat=True)

        qs = (
            ActivityLog.objects.filter(project_id__in=user_project_ids)
            .select_related("actor")
            .order_by("-created_at")
        )
        limit = min(int(request.query_params.get("limit", 20)), 100)

        def _time_ago(dt):
            diff = tz.now() - dt
            s = int(diff.total_seconds())
            if s < 60:
                return f"{s}s ago"
            if s < 3600:
                return f"{s // 60}m ago"
            if s < 86400:
                return f"{s // 3600}h ago"
            return f"{s // 86400}d ago"

        result = []
        for entry in qs[:limit]:
            target = ""
            if entry.new_value:
                target = entry.new_value.get("title", entry.new_value.get("name", ""))
            result.append({
                "id": str(entry.id),
                "actor_name": entry.actor.display_name,
                "action": entry.action,
                "target": target,
                "time_ago": _time_ago(entry.created_at),
                "entity_type": entry.entity_type,
                "entity_id": str(entry.entity_id),
            })

        return Response(result)



class MyTasksView(APIView):
    """
    GET /api/tasks/my/ — tasks assigned to the current user in the active workspace.
    Excludes cancelled and deleted tasks.

    Query params:
      status: comma-separated list of statuses to filter by
    """

    def get(self, request):
        from projects.request_helpers import _active_ws
        active_ws = _active_ws(request)
        qs = (
            Task.objects.filter(assigned_to=request.user, deleted_at__isnull=True, **ws_filter)
            .exclude(status="cancelled")
            .select_related("project", "assigned_to", "created_by", "sprint", "board_column")
            .prefetch_related("task_labels__label")
            .order_by("status", "position", "created_at")
        )
        if active_ws is not None:
            qs = qs.filter(project__workspace=active_ws)

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status__in=[s.strip() for s in status_filter.split(",")])

        return Response(TaskSerializer(qs, many=True).data)


# ---------------------------------------------------------------------------
# Attachment views
# ---------------------------------------------------------------------------

class TaskAttachmentListCreateView(APIView):
    """
    GET  /api/tasks/<pk>/attachments/  — list task attachments
    POST /api/tasks/<pk>/attachments/  — upload a file (multipart/form-data)
    """

    def get(self, request, pk):
        from .models import Attachment
        from .serializers import AttachmentSerializer
        task = get_object_or_404(Task, pk=pk, deleted_at__isnull=True)
        if not AccessControlService.can_view_task(request.user, task):
            return Response({"detail": "Not found."}, status=404)
        attachments = Attachment.objects.filter(task=task).select_related("uploaded_by")
        return Response({"results": AttachmentSerializer(attachments, many=True, context={"request": request}).data})

    def post(self, request, pk):
        from .models import Comment
        from .serializers import AttachmentSerializer
        task = get_object_or_404(Task, pk=pk, deleted_at__isnull=True)
        if not AccessControlService.can_edit_task(request.user, task):
            return Response({"detail": "Forbidden."}, status=403)

        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response({"detail": "No file provided."}, status=400)

        comment = None
        if comment_id := request.data.get("comment_id"):
            comment = get_object_or_404(Comment, pk=comment_id, task=task)

        try:
            attachment = AttachmentService.upload(task, uploaded_file, request.user, comment)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        return Response(AttachmentSerializer(attachment, context={"request": request}).data, status=201)


class AttachmentDetailView(APIView):
    """DELETE /api/attachments/<pk>/"""

    def delete(self, request, pk):
        from .models import Attachment
        attachment = get_object_or_404(Attachment, pk=pk)
        user = request.user

        is_uploader = attachment.uploaded_by_id == user.pk
        is_elevated = user.has_elevated_access()
        is_manager = False
        if attachment.task:
            membership = ProjectMember.objects.filter(
                project=attachment.task.project, user=user
            ).first()
            is_manager = membership and membership.role in (ProjectRole.PO, ProjectRole.PM)

        if not (is_uploader or is_elevated or is_manager):
            return Response({"detail": "Forbidden."}, status=403)

        AttachmentService.delete_attachment(attachment, request.user)
        return Response(status=204)


class AttachmentDownloadView(APIView):
    """
    GET /api/attachments/<pk>/download/

    Streams the attachment file after verifying the caller has task-view access.
    This endpoint is the only authorized download path — direct media URLs are
    not exposed in the API (see AttachmentSerializer.get_download_url).
    """

    def get(self, request, pk):
        from .models import Attachment
        attachment = get_object_or_404(Attachment, pk=pk)
        if attachment.task and not AccessControlService.can_view_task(request.user, attachment.task):
            return Response({"detail": "Not found."}, status=404)

        from django.core.files.storage import default_storage
        from django.http import StreamingHttpResponse

        if not default_storage.exists(attachment.storage_key):
            return Response({"detail": "File not found in storage."}, status=404)

        file_obj = default_storage.open(attachment.storage_key, "rb")
        response = StreamingHttpResponse(file_obj, content_type=attachment.mime_type)
        safe_filename = attachment.filename.replace('"', '\\"')
        response["Content-Disposition"] = f'attachment; filename="{safe_filename}"'
        response["Content-Length"] = attachment.file_size_bytes
        return response


class TaskSearchView(APIView):
    """
    GET /api/tasks/search/?q=<query>
    Cross-project full-text search across all projects the caller can access.
    Returns up to 20 matching tasks ordered by relevance (recency).
    """

    def get(self, request):
        from projects.request_helpers import _active_ws
        active_ws = _active_ws(request)

        q = request.query_params.get("q", "").strip()
        if len(q) < 2:
            return Response([])

        # Determine which projects the caller can see (scoped to active workspace)
        if request.user.has_elevated_access():
            project_qs = Project.objects.filter(status=ProjectStatus.ACTIVE)
        else:
            project_qs = Project.objects.filter(
                id__in=ProjectMember.objects.filter(user=request.user).values("project_id"),
                status=ProjectStatus.ACTIVE,
            )
        if active_ws is not None:
            project_qs = project_qs.filter(workspace=active_ws)
        accessible_pids = project_qs.values_list("id", flat=True)

        tasks = (
            Task.objects.filter(
                project_id__in=accessible_pids,
                deleted_at__isnull=True,
                title__icontains=q,
            )
        if active_ws:
            project_qs = project_qs.filter(workspace=active_ws)
        accessible_pids = project_qs.values_list("id", flat=True)

        qs = Task.objects.filter(
            project_id__in=accessible_pids,
            deleted_at__isnull=True,
            title__icontains=q,
        ).select_related("project", "assigned_to")

        # Guests only see public tasks in their accessible projects — filter in DB
        if not request.user.has_elevated_access():
            guest_project_ids = ProjectMember.objects.filter(
                user=request.user, role=ProjectRole.GU
            ).values_list("project_id", flat=True)
            qs = qs.exclude(project_id__in=guest_project_ids, is_private=True)

        tasks = qs.order_by("-updated_at")[:20]

        return Response(TaskSearchResultSerializer(tasks, many=True).data)
