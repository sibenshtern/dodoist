from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import GlobalRole, User

from .models import (
    Label,
    Project,
    ProjectMember,
    ProjectRole,
    ProjectStatus,
    Sprint,
    SprintStatus,
    Workspace,
    WorkspaceMember,
)
from .serializers import (
    LabelCreateSerializer,
    LabelSerializer,
    LabelUpdateSerializer,
    ProjectCreateSerializer,
    ProjectMemberAddSerializer,
    ProjectMemberSerializer,
    ProjectMemberUpdateSerializer,
    ProjectSerializer,
    ProjectUpdateSerializer,
    WorkspaceCreateSerializer,
    WorkspaceMemberSerializer,
    WorkspaceSerializer,
    WorkspaceUpdateSerializer,
)
from .services import ProjectService, WorkspaceService


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
    """
    GET  /api/workspaces/  — list current user's workspaces
    POST /api/workspaces/  — create a workspace
    """

    def get(self, request):
        if request.user.has_elevated_access():
            qs = Workspace.objects.all().select_related("owner")
        else:
            qs = Workspace.objects.filter(members__user=request.user).select_related("owner")

        is_personal = request.query_params.get("is_personal")
        if is_personal is not None:
            qs = qs.filter(is_personal=is_personal.lower() == "true")

        return Response(WorkspaceSerializer(qs, many=True).data)

    def post(self, request):
        serializer = WorkspaceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            workspace = WorkspaceService.create_workspace(
                owner=request.user,
                name=data["name"],
                slug=data["slug"] or None,
                description=data["description"],
                plan=data["plan"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(WorkspaceSerializer(workspace).data, status=201)


class WorkspaceDetailView(APIView):
    """
    GET    /api/workspaces/<slug>/  — retrieve workspace details
    PATCH  /api/workspaces/<slug>/  — update metadata (owner or SA)
    DELETE /api/workspaces/<slug>/  — delete workspace (SA only)
    """

    def get(self, request, slug):
        workspace = _get_workspace(slug)
        if not request.user.has_elevated_access() and not _is_workspace_member(workspace, request.user):
            return Response({"detail": "Not found."}, status=404)
        return Response(WorkspaceSerializer(workspace).data)

    def patch(self, request, slug):
        workspace = _get_workspace(slug)
        if not request.user.has_elevated_access() and workspace.owner_id != request.user.pk:
            return Response(
                {"detail": "Only the workspace owner can update this workspace."}, status=403
            )
        serializer = WorkspaceUpdateSerializer(workspace, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        workspace = serializer.save()
        return Response(WorkspaceSerializer(workspace).data)

    def delete(self, request, slug):
        workspace = _get_workspace(slug)
        if not request.user.has_elevated_access():
            return Response(
                {"detail": "Only system administrators can delete workspaces."}, status=403
            )
        workspace.delete()
        return Response(status=204)


class WorkspaceMemberListView(APIView):
    """
    GET  /api/workspaces/<slug>/members/  — list workspace members
    POST /api/workspaces/<slug>/members/  — add a member
    """

    def get(self, request, slug):
        workspace = _get_workspace(slug)
        if not request.user.has_elevated_access() and not _is_workspace_member(workspace, request.user):
            return Response({"detail": "Not found."}, status=404)
        members = WorkspaceMember.objects.filter(workspace=workspace).select_related("user")
        return Response(WorkspaceMemberSerializer(members, many=True).data)

    def post(self, request, slug):
        workspace = _get_workspace(slug)
        if not request.user.has_elevated_access() and workspace.owner_id != request.user.pk:
            return Response(
                {"detail": "Only the workspace owner can add members."}, status=403
            )
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"detail": "user_id is required."}, status=400)
        try:
            user = User.objects.get(pk=user_id, is_active=True)
        except (User.DoesNotExist, ValueError):
            return Response({"detail": "User not found."}, status=404)
        member = WorkspaceService.add_member(workspace, user)
        member_with_user = WorkspaceMember.objects.select_related("user").get(pk=member.pk)
        return Response(WorkspaceMemberSerializer(member_with_user).data, status=201)


class WorkspaceMemberDetailView(APIView):
    """
    DELETE /api/workspaces/<slug>/members/<user_id>/  — remove a member
    """

    def delete(self, request, slug, user_id):
        workspace = _get_workspace(slug)
        if not request.user.has_elevated_access() and workspace.owner_id != request.user.pk:
            return Response(
                {"detail": "Only the workspace owner can remove members."}, status=403
            )
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
