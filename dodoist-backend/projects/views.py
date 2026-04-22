from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import GlobalRole, User

from django.utils import timezone as tz

from .models import (
    Board,
    BoardColumn,
    Label,
    Project,
    ProjectMember,
    ProjectRole,
    ProjectStatus,
    ProjectType,
    Sprint,
    SprintStatus,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)
from .serializers import (
    BoardColumnCreateSerializer,
    BoardColumnSerializer,
    BoardColumnUpdateSerializer,
    BoardCreateSerializer,
    BoardSerializer,
    BoardUpdateSerializer,
    LabelCreateSerializer,
    LabelSerializer,
    LabelUpdateSerializer,
    ProjectCreateSerializer,
    ProjectMemberAddSerializer,
    ProjectMemberSerializer,
    ProjectMemberUpdateSerializer,
    ProjectSerializer,
    ProjectUpdateSerializer,
    SprintCompleteSerializer,
    SprintCreateSerializer,
    SprintSerializer,
    SprintUpdateSerializer,
    WorkspaceCreateSerializer,
    WorkspaceMemberAddSerializer,
    WorkspaceMemberSerializer,
    WorkspaceMemberUpdateSerializer,
    WorkspaceSerializer,
    WorkspaceUpdateSerializer,
)
from .services import ProjectService, SprintService, WorkspaceService


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _get_workspace(slug: str) -> Workspace:
    return get_object_or_404(Workspace.objects.select_related("owner"), slug=slug)


def _is_workspace_member(workspace: Workspace, user: User) -> bool:
    return WorkspaceMember.objects.filter(workspace=workspace, user=user).exists()


def _get_project_membership(project: Project, user: User):
    return ProjectMember.objects.filter(project=project, user=user).first()


def _can_view_project(user: User, project: Project) -> bool:
    if user.has_elevated_access():
        return True
    if not WorkspaceMember.objects.filter(workspace=project.workspace, user=user).exists():
        return False
    if not project.is_private:
        return True
    return ProjectMember.objects.filter(project=project, user=user).exists()


def _can_manage_project(user: User, project: Project) -> bool:
    """PO, PM, SA, GA may update project settings."""
    if user.has_elevated_access():
        return True
    m = _get_project_membership(project, user)
    return m is not None and m.role in (ProjectRole.PO, ProjectRole.PM)


def _can_admin_project(user: User, project: Project) -> bool:
    """SA or PO only: archive, delete, manage members."""
    if user.global_role == GlobalRole.SA:
        return True
    m = _get_project_membership(project, user)
    return m is not None and m.role == ProjectRole.PO


def _project_qs_with_prefetch():
    active_sprint_prefetch = Prefetch(
        "sprints",
        queryset=Sprint.objects.filter(status=SprintStatus.ACTIVE),
        to_attr="active_sprints",
    )
    return Project.objects.select_related("created_by").prefetch_related(
        "members", active_sprint_prefetch
    )


# ---------------------------------------------------------------------------
# Workspace views
# ---------------------------------------------------------------------------

class WorkspaceListCreateView(APIView):
    def get(self, request):
        if request.user.has_elevated_access():
            qs = Workspace.objects.all().select_related("owner")
        else:
            qs = Workspace.objects.filter(
                members__user=request.user, deleted_at__isnull=True
            ).select_related("owner")

        is_personal = request.query_params.get("is_personal")
        if is_personal is not None:
            qs = qs.filter(is_personal=is_personal.lower() == "true")

        return Response(WorkspaceSerializer(qs, many=True).data)

    def post(self, request):
        serializer = WorkspaceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            workspace = WorkspaceService.create_team_workspace(
                owner=request.user,
                name=data["name"],
                slug=data["slug"] or None,
                description=data["description"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(WorkspaceSerializer(workspace).data, status=201)


class WorkspaceDetailView(APIView):
    def get(self, request, slug):
        workspace = _get_workspace(slug)
        if not request.user.has_elevated_access() and not _is_workspace_member(workspace, request.user):
            return Response({"detail": "Not found."}, status=404)
        return Response(WorkspaceSerializer(workspace).data)

    def patch(self, request, slug):
        workspace = _get_workspace(slug)
        from tasks.services import AccessControlService
        if not request.user.has_elevated_access() and not AccessControlService.is_workspace_admin_or_owner(request.user, workspace):
            return Response({"detail": "Only Owner or Admin can update workspace settings."}, status=403)
        serializer = WorkspaceUpdateSerializer(workspace, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        workspace = serializer.save()
        return Response(WorkspaceSerializer(workspace).data)

    def delete(self, request, slug):
        workspace = _get_workspace(slug)
        try:
            WorkspaceService.soft_delete(workspace, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(WorkspaceSerializer(workspace).data, status=200)


class WorkspaceRestoreView(APIView):
    def post(self, request, slug):
        workspace = get_object_or_404(Workspace, slug=slug)
        try:
            WorkspaceService.restore(workspace, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(WorkspaceSerializer(workspace).data)


class WorkspaceTransferOwnershipView(APIView):
    def post(self, request, slug):
        workspace = _get_workspace(slug)
        new_owner_id = request.data.get("new_owner_id")
        if not new_owner_id:
            return Response({"detail": "new_owner_id is required."}, status=400)
        try:
            new_owner = User.objects.get(pk=new_owner_id, is_active=True)
        except (User.DoesNotExist, ValueError):
            return Response({"detail": "User not found."}, status=404)
        try:
            WorkspaceService.transfer_ownership(workspace, new_owner, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(WorkspaceSerializer(workspace).data)


class WorkspaceLeaveView(APIView):
    def post(self, request, slug):
        workspace = _get_workspace(slug)
        try:
            WorkspaceService.leave(workspace, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(status=204)


class WorkspaceMemberListView(APIView):
    def get(self, request, slug):
        workspace = _get_workspace(slug)
        if not request.user.has_elevated_access() and not _is_workspace_member(workspace, request.user):
            return Response({"detail": "Not found."}, status=404)
        members = WorkspaceMember.objects.filter(workspace=workspace).select_related("user")
        return Response(WorkspaceMemberSerializer(members, many=True).data)

    def post(self, request, slug):
        workspace = _get_workspace(slug)
        from tasks.services import AccessControlService
        if not request.user.has_elevated_access() and not AccessControlService.is_workspace_admin_or_owner(request.user, workspace):
            return Response({"detail": "Only Owner or Admin can add members."}, status=403)
        serializer = WorkspaceMemberAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user = User.objects.get(pk=data["user_id"], is_active=True)
        except (User.DoesNotExist, ValueError):
            return Response({"detail": "User not found."}, status=404)
        try:
            member = WorkspaceService.add_member(workspace, user, role=data["role"], invited_by=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        member_with_user = WorkspaceMember.objects.select_related("user").get(pk=member.pk)
        return Response(WorkspaceMemberSerializer(member_with_user).data, status=201)


class WorkspaceMemberDetailView(APIView):
    def patch(self, request, slug, user_id):
        workspace = _get_workspace(slug)
        from tasks.services import AccessControlService
        if not request.user.has_elevated_access() and not AccessControlService.is_workspace_admin_or_owner(request.user, workspace):
            return Response({"detail": "Only Owner or Admin can change member roles."}, status=403)
        serializer = WorkspaceMemberUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError):
            return Response({"detail": "User not found."}, status=404)
        try:
            member = WorkspaceService.change_role(workspace, user, serializer.validated_data["role"], request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(WorkspaceMemberSerializer(WorkspaceMember.objects.select_related("user").get(pk=member.pk)).data)

    def delete(self, request, slug, user_id):
        workspace = _get_workspace(slug)
        from tasks.services import AccessControlService
        if not request.user.has_elevated_access() and not AccessControlService.is_workspace_admin_or_owner(request.user, workspace):
            return Response({"detail": "Only Owner or Admin can remove members."}, status=403)
        try:
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError):
            return Response({"detail": "User not found."}, status=404)
        try:
            WorkspaceService.remove_member(workspace, user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(status=204)


# ---------------------------------------------------------------------------
# Project views
# ---------------------------------------------------------------------------

class ProjectListCreateView(APIView):
    """
    GET  /api/workspaces/<slug>/projects/  — list projects in a workspace
    POST /api/workspaces/<slug>/projects/  — create a project
    """

    def get(self, request, slug):
        workspace = get_object_or_404(Workspace, slug=slug)

        if not request.user.has_elevated_access() and not _is_workspace_member(workspace, request.user):
            return Response({"detail": "Not found."}, status=404)

        qs = _project_qs_with_prefetch().filter(workspace=workspace).exclude(
            status=ProjectStatus.DELETED
        )

        if not request.user.has_elevated_access():
            member_project_ids = ProjectMember.objects.filter(
                project__workspace=workspace, user=request.user
            ).values_list("project_id", flat=True)
            qs = qs.filter(Q(is_private=False) | Q(id__in=member_project_ids))

        status = request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)

        project_type = request.query_params.get("type")
        if project_type:
            qs = qs.filter(type=project_type)

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(key__icontains=search))

        return Response(ProjectSerializer(qs, many=True, context={"request": request}).data)

    def post(self, request, slug):
        workspace = get_object_or_404(Workspace, slug=slug)

        if not request.user.has_elevated_access() and not _is_workspace_member(workspace, request.user):
            return Response(
                {"detail": "You must be a workspace member to create projects."}, status=403
            )

        serializer = ProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            project = ProjectService.create_project(
                workspace=workspace,
                creator=request.user,
                name=data["name"],
                key=data["key"],
                project_type=data["type"],
                is_private=data["is_private"],
                description=data["description"],
                color=data["color"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        project = _project_qs_with_prefetch().get(pk=project.pk)
        return Response(ProjectSerializer(project, context={"request": request}).data, status=201)


class ProjectDetailView(APIView):
    """
    GET    /api/projects/<uuid>/  — retrieve project details
    PATCH  /api/projects/<uuid>/  — update settings (PO, PM, SA, GA)
    DELETE /api/projects/<uuid>/  — soft delete (PO, SA)
    """

    def _get_project(self, pk):
        return get_object_or_404(_project_qs_with_prefetch(), pk=pk)

    def get(self, request, pk):
        project = self._get_project(pk)
        if project.status == ProjectStatus.DELETED:
            return Response({"detail": "Not found."}, status=404)
        if not _can_view_project(request.user, project):
            return Response({"detail": "Not found."}, status=404)
        return Response(ProjectSerializer(project, context={"request": request}).data)

    def patch(self, request, pk):
        project = self._get_project(pk)
        if project.status == ProjectStatus.DELETED:
            return Response({"detail": "Not found."}, status=404)
        if not _can_manage_project(request.user, project):
            return Response({"detail": "Permission denied."}, status=403)
        serializer = ProjectUpdateSerializer(project, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        project = serializer.save()
        project = _project_qs_with_prefetch().get(pk=project.pk)
        return Response(ProjectSerializer(project, context={"request": request}).data)

    def delete(self, request, pk):
        project = self._get_project(pk)
        if project.status == ProjectStatus.DELETED:
            return Response({"detail": "Not found."}, status=404)
        if not _can_admin_project(request.user, project):
            return Response({"detail": "Permission denied."}, status=403)
        ProjectService.delete_project(project)
        return Response(status=204)


class ProjectArchiveView(APIView):
    """
    POST /api/projects/<uuid>/archive/  — archive a project (PO, SA)
    """

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        if not _can_admin_project(request.user, project):
            return Response({"detail": "Permission denied."}, status=403)
        try:
            project = ProjectService.archive_project(project)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        project = _project_qs_with_prefetch().get(pk=project.pk)
        return Response(ProjectSerializer(project, context={"request": request}).data)


class ProjectUnarchiveView(APIView):
    """
    POST /api/projects/<uuid>/unarchive/  — restore an archived project (PO, SA)
    """

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        if not _can_admin_project(request.user, project):
            return Response({"detail": "Permission denied."}, status=403)
        try:
            project = ProjectService.restore_project(project)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        project = _project_qs_with_prefetch().get(pk=project.pk)
        return Response(ProjectSerializer(project, context={"request": request}).data)


class ProjectMemberListView(APIView):
    """
    GET  /api/projects/<uuid>/members/  — list members with roles
    POST /api/projects/<uuid>/members/  — add a member
    """

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        if not _can_view_project(request.user, project):
            return Response({"detail": "Not found."}, status=404)
        members = ProjectMember.objects.filter(project=project).select_related("user", "invited_by")
        return Response(ProjectMemberSerializer(members, many=True).data)

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        if not _can_manage_project(request.user, project):
            return Response({"detail": "Permission denied."}, status=403)
        serializer = ProjectMemberAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user_id"]
        role = serializer.validated_data["role"]
        try:
            member = ProjectService.add_member(project, user, role)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        member = ProjectMember.objects.select_related("user", "invited_by").get(pk=member.pk)
        return Response(ProjectMemberSerializer(member).data, status=201)


class ProjectMemberDetailView(APIView):
    """
    PATCH  /api/projects/<uuid>/members/<user_id>/  — update a member's role (PO, SA)
    DELETE /api/projects/<uuid>/members/<user_id>/  — remove a member (PO, SA)
    """

    def _get_member(self, project, user_id):
        user = get_object_or_404(User, pk=user_id)
        return get_object_or_404(ProjectMember, project=project, user=user), user

    def patch(self, request, pk, user_id):
        project = get_object_or_404(Project, pk=pk)
        if not _can_admin_project(request.user, project):
            return Response({"detail": "Permission denied."}, status=403)
        _, user = self._get_member(project, user_id)
        serializer = ProjectMemberUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            member = ProjectService.add_member(project, user, serializer.validated_data["role"])
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        member = ProjectMember.objects.select_related("user", "invited_by").get(pk=member.pk)
        return Response(ProjectMemberSerializer(member).data)

    def delete(self, request, pk, user_id):
        project = get_object_or_404(Project, pk=pk)
        if not _can_admin_project(request.user, project):
            return Response({"detail": "Permission denied."}, status=403)
        _, user = self._get_member(project, user_id)
        try:
            ProjectService.remove_member(project, user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(status=204)


# ---------------------------------------------------------------------------
# Label views
# ---------------------------------------------------------------------------

class LabelListCreateView(APIView):
    """
    GET  /api/workspaces/<slug>/labels/  — list workspace labels
    POST /api/workspaces/<slug>/labels/  — create a label
    """

    def get(self, request, slug):
        workspace = get_object_or_404(Workspace, slug=slug)
        if not request.user.has_elevated_access() and not _is_workspace_member(workspace, request.user):
            return Response({"detail": "Not found."}, status=404)
        labels = Label.objects.filter(workspace=workspace).select_related("created_by")
        return Response(LabelSerializer(labels, many=True).data)

    def post(self, request, slug):
        workspace = get_object_or_404(Workspace, slug=slug)
        if not request.user.has_elevated_access() and not _is_workspace_member(workspace, request.user):
            return Response({"detail": "Not found."}, status=404)
        serializer = LabelCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if Label.objects.filter(workspace=workspace, name=data["name"]).exists():
            return Response(
                {"detail": "A label with this name already exists in this workspace."}, status=400
            )
        label = Label.objects.create(
            workspace=workspace,
            name=data["name"],
            color=data["color"],
            created_by=request.user,
        )
        return Response(LabelSerializer(label).data, status=201)


class LabelDetailView(APIView):
    """
    PATCH  /api/workspaces/<slug>/labels/<uuid>/  — update a label
    DELETE /api/workspaces/<slug>/labels/<uuid>/  — delete a label
    """

    def _get_label(self, slug, label_id):
        workspace = get_object_or_404(Workspace, slug=slug)
        label = get_object_or_404(Label.objects.select_related("created_by"), pk=label_id, workspace=workspace)
        return workspace, label

    def patch(self, request, slug, label_id):
        workspace, label = self._get_label(slug, label_id)
        if not request.user.has_elevated_access() and not _is_workspace_member(workspace, request.user):
            return Response({"detail": "Not found."}, status=404)
        serializer = LabelUpdateSerializer(label, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        new_name = serializer.validated_data.get("name")
        if new_name and new_name != label.name:
            if Label.objects.filter(workspace=workspace, name=new_name).exists():
                return Response(
                    {"detail": "A label with this name already exists in this workspace."}, status=400
                )
        label = serializer.save()
        return Response(LabelSerializer(label).data)

    def delete(self, request, slug, label_id):
        workspace, label = self._get_label(slug, label_id)
        if not request.user.has_elevated_access() and not _is_workspace_member(workspace, request.user):
            return Response({"detail": "Not found."}, status=404)
        label.delete()
        return Response(status=204)


# ---------------------------------------------------------------------------
# Sprint views
# ---------------------------------------------------------------------------

def _can_manage_sprint(user: User, project: Project) -> bool:
    """PM, PO, SA can manage sprints."""
    if user.has_elevated_access():
        return True
    m = _get_project_membership(project, user)
    return m is not None and m.role in (ProjectRole.PO, ProjectRole.PM)


class ProjectSprintListView(APIView):
    """
    GET  /api/projects/<pk>/sprints/  — list sprints
    POST /api/projects/<pk>/sprints/  — create sprint (PM/PO/SA)
    """

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        if not _can_view_project(request.user, project):
            return Response({"detail": "Not found."}, status=404)
        qs = Sprint.objects.filter(project=project).select_related("created_by").order_by("-created_at")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(SprintSerializer(qs, many=True).data)

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        if not _can_manage_sprint(request.user, project):
            return Response({"detail": "Insufficient permissions."}, status=403)
        if project.type != ProjectType.SCRUM:
            return Response({"detail": "Sprints are only available for Scrum projects."}, status=400)
        serializer = SprintCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        sprint = Sprint.objects.create(
            project=project,
            created_by=request.user,
            name=data["name"],
            goal=data.get("goal", ""),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
        )
        sprint = Sprint.objects.select_related("created_by").get(pk=sprint.pk)
        return Response(SprintSerializer(sprint).data, status=201)


class SprintDetailView(APIView):
    """
    GET    /api/sprints/<pk>/  — get sprint with task stats
    PATCH  /api/sprints/<pk>/  — update sprint (PM/PO/SA)
    DELETE /api/sprints/<pk>/  — delete planned sprint (PM/PO/SA)
    """

    def _get_sprint(self, pk):
        return get_object_or_404(Sprint.objects.select_related("project", "created_by"), pk=pk)

    def get(self, request, pk):
        sprint = self._get_sprint(pk)
        if not _can_view_project(request.user, sprint.project):
            return Response({"detail": "Not found."}, status=404)
        from tasks.models import Task
        from projects.models import TaskStatus
        sprint_tasks = Task.objects.filter(sprint=sprint, deleted_at__isnull=True)
        task_stats = {
            "total": sprint_tasks.count(),
            "completed": sprint_tasks.filter(status=TaskStatus.DONE).count(),
            "in_progress": sprint_tasks.filter(status=TaskStatus.IN_PROGRESS).count(),
            "total_story_points": sum(t.story_points or 0 for t in sprint_tasks),
            "completed_story_points": sum(
                t.story_points or 0 for t in sprint_tasks.filter(status=TaskStatus.DONE)
            ),
        }
        data = SprintSerializer(sprint).data
        data["task_stats"] = task_stats
        return Response(data)

    def patch(self, request, pk):
        sprint = self._get_sprint(pk)
        if not _can_manage_sprint(request.user, sprint.project):
            return Response({"detail": "Insufficient permissions."}, status=403)
        serializer = SprintUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(sprint, field, value)
        sprint.save()
        return Response(SprintSerializer(sprint).data)

    def delete(self, request, pk):
        sprint = self._get_sprint(pk)
        if not _can_manage_sprint(request.user, sprint.project):
            return Response({"detail": "Insufficient permissions."}, status=403)
        if sprint.status != SprintStatus.PLANNED:
            return Response({"detail": "Only planned sprints can be deleted."}, status=400)
        sprint.delete()
        return Response(status=204)


class SprintStartView(APIView):
    """POST /api/sprints/<pk>/start/"""

    def post(self, request, pk):
        sprint = get_object_or_404(Sprint.objects.select_related("project", "created_by"), pk=pk)
        if not _can_manage_sprint(request.user, sprint.project):
            return Response({"detail": "Insufficient permissions."}, status=403)
        try:
            sprint = SprintService.start_sprint(sprint)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(SprintSerializer(sprint).data)


class SprintCompleteView(APIView):
    """POST /api/sprints/<pk>/complete/"""

    def post(self, request, pk):
        sprint = get_object_or_404(Sprint.objects.select_related("project", "created_by"), pk=pk)
        if not _can_manage_sprint(request.user, sprint.project):
            return Response({"detail": "Insufficient permissions."}, status=403)
        serializer = SprintCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            sprint = SprintService.complete_sprint(sprint)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        # Handle incomplete tasks
        from tasks.models import Task
        from projects.models import TaskStatus
        incomplete_tasks = Task.objects.filter(sprint=sprint, deleted_at__isnull=True).exclude(
            status__in=[TaskStatus.DONE, TaskStatus.CANCELLED]
        )
        if data["incomplete_tasks_action"] == "backlog":
            incomplete_tasks.update(sprint=None)
        elif data["incomplete_tasks_action"] == "next_sprint":
            next_sprint = get_object_or_404(Sprint, pk=data["next_sprint_id"])
            incomplete_tasks.update(sprint=next_sprint)

        return Response(SprintSerializer(sprint).data)


class SprintTaskView(APIView):
    """
    POST   /api/sprints/<pk>/tasks/           — add task to sprint
    DELETE /api/sprints/<pk>/tasks/<task_id>/ — remove task from sprint
    """

    def post(self, request, pk):
        sprint = get_object_or_404(Sprint.objects.select_related("project"), pk=pk)
        if not _can_manage_sprint(request.user, sprint.project):
            return Response({"detail": "Insufficient permissions."}, status=403)
        task_id = request.data.get("task_id")
        if not task_id:
            return Response({"detail": "task_id is required."}, status=400)
        from tasks.models import Task
        task = get_object_or_404(Task, pk=task_id, project=sprint.project, deleted_at__isnull=True)
        task.sprint = sprint
        task.save(update_fields=["sprint", "updated_at"])
        return Response({"task_id": str(task.pk), "sprint_id": str(sprint.pk)}, status=201)

    def delete(self, request, pk, task_id):
        sprint = get_object_or_404(Sprint.objects.select_related("project"), pk=pk)
        if not _can_manage_sprint(request.user, sprint.project):
            return Response({"detail": "Insufficient permissions."}, status=403)
        from tasks.models import Task
        task = get_object_or_404(Task, pk=task_id, sprint=sprint, deleted_at__isnull=True)
        task.sprint = None
        task.save(update_fields=["sprint", "updated_at"])
        return Response(status=204)


# ---------------------------------------------------------------------------
# Board & BoardColumn views
# ---------------------------------------------------------------------------

class ProjectBoardListView(APIView):
    """
    GET  /api/projects/<pk>/boards/  — list boards
    POST /api/projects/<pk>/boards/  — create board (PM/PO/SA)
    """

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        if not _can_view_project(request.user, project):
            return Response({"detail": "Not found."}, status=404)
        boards = Board.objects.filter(project=project).select_related("created_by").order_by("created_at")
        return Response(BoardSerializer(boards, many=True).data)

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        if not _can_manage_project(request.user, project):
            return Response({"detail": "Insufficient permissions."}, status=403)
        serializer = BoardCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        board = Board.objects.create(
            project=project,
            created_by=request.user,
            name=data["name"],
            type=data["type"],
            is_default=data.get("is_default", False),
        )
        board = Board.objects.select_related("created_by").get(pk=board.pk)
        return Response(BoardSerializer(board).data, status=201)


class BoardDetailView(APIView):
    """
    GET    /api/boards/<pk>/  — get board
    PATCH  /api/boards/<pk>/  — update board (PM/PO/SA)
    DELETE /api/boards/<pk>/  — delete board (PM/PO/SA)
    """

    def _get_board(self, pk):
        return get_object_or_404(Board.objects.select_related("project", "created_by"), pk=pk)

    def get(self, request, pk):
        board = self._get_board(pk)
        if not _can_view_project(request.user, board.project):
            return Response({"detail": "Not found."}, status=404)
        return Response(BoardSerializer(board).data)

    def patch(self, request, pk):
        board = self._get_board(pk)
        if not _can_manage_project(request.user, board.project):
            return Response({"detail": "Insufficient permissions."}, status=403)
        serializer = BoardUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(board, field, value)
        board.save()
        return Response(BoardSerializer(board).data)

    def delete(self, request, pk):
        board = self._get_board(pk)
        if not _can_manage_project(request.user, board.project):
            return Response({"detail": "Insufficient permissions."}, status=403)
        board.delete()
        return Response(status=204)


class BoardColumnListView(APIView):
    """
    GET  /api/boards/<pk>/columns/  — list columns
    POST /api/boards/<pk>/columns/  — create column (PM/PO/SA)
    """

    def get(self, request, pk):
        board = get_object_or_404(Board.objects.select_related("project"), pk=pk)
        if not _can_view_project(request.user, board.project):
            return Response({"detail": "Not found."}, status=404)
        columns = BoardColumn.objects.filter(board=board).order_by("position")
        return Response(BoardColumnSerializer(columns, many=True).data)

    def post(self, request, pk):
        board = get_object_or_404(Board.objects.select_related("project"), pk=pk)
        if not _can_manage_project(request.user, board.project):
            return Response({"detail": "Insufficient permissions."}, status=403)
        serializer = BoardColumnCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        column = BoardColumn.objects.create(board=board, **data)
        return Response(BoardColumnSerializer(column).data, status=201)


class BoardColumnDetailView(APIView):
    """
    PATCH  /api/boards/<board_pk>/columns/<pk>/  — update column
    DELETE /api/boards/<board_pk>/columns/<pk>/  — delete column
    """

    def _get_column(self, board_pk, pk):
        board = get_object_or_404(Board.objects.select_related("project"), pk=board_pk)
        column = get_object_or_404(BoardColumn, pk=pk, board=board)
        return board, column

    def patch(self, request, board_pk, pk):
        board, column = self._get_column(board_pk, pk)
        if not _can_manage_project(request.user, board.project):
            return Response({"detail": "Insufficient permissions."}, status=403)
        serializer = BoardColumnUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(column, field, value)
        column.save()
        return Response(BoardColumnSerializer(column).data)

    def delete(self, request, board_pk, pk):
        board, column = self._get_column(board_pk, pk)
        if not _can_manage_project(request.user, board.project):
            return Response({"detail": "Insufficient permissions."}, status=403)
        column.delete()
        return Response(status=204)
