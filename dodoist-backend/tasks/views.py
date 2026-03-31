from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.models import Label, Project, ProjectMember, ProjectRole
from users.models import User

from .models import Task, TaskDependency, TaskGuestAccess
from .serializers import (
    ProjectTaskCreateSerializer,
    TaskAssignmentAddSerializer,
    TaskAssignmentSerializer,
    TaskCreateSerializer,
    TaskDependencyCreateSerializer,
    TaskDependencySerializer,
    TaskGuestAccessCreateSerializer,
    TaskGuestAccessSerializer,
    TaskLabelAddSerializer,
    TaskSerializer,
    TaskUpdateSerializer,
)
from .services import AccessControlService, TaskService

_VALID_SORT_FIELDS = {"created_at", "due_date", "priority", "position"}


def _can_manage_guest_access(user, task):
    if user.has_elevated_access():
        return True
    membership = ProjectMember.objects.filter(project=task.project, user=user).first()
    return membership and membership.role in (ProjectRole.PO, ProjectRole.PM)


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
        serializer = TaskCreateSerializer(data=request.data)
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
    POST /api/tasks/<uuid>/assignments/ — add a co-assignee
    """

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
    POST /api/tasks/<uuid>/labels/ — attach a label to a task
    """

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
    DELETE /api/tasks/<uuid>/dependencies/<dep_id>/ — remove a dependency
    """

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
