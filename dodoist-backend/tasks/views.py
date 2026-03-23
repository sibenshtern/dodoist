from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.models import Project, ProjectMember, ProjectRole

from .models import Task
from .serializers import TaskCreateSerializer, TaskSerializer, TaskUpdateSerializer
from .services import AccessControlService, TaskService


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
