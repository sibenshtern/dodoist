from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User

from .models import Workspace, WorkspaceMember
from .serializers import (
    WorkspaceCreateSerializer,
    WorkspaceMemberSerializer,
    WorkspaceSerializer,
    WorkspaceUpdateSerializer,
)
from .services import WorkspaceService


def _get_workspace(slug: str) -> Workspace:
    return get_object_or_404(Workspace.objects.select_related("owner"), slug=slug)


def _is_member(workspace: Workspace, user: User) -> bool:
    return WorkspaceMember.objects.filter(workspace=workspace, user=user).exists()


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
        if not request.user.has_elevated_access() and not _is_member(workspace, request.user):
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
        if not request.user.has_elevated_access() and not _is_member(workspace, request.user):
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
