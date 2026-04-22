from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User

from .invitations import InvitationService
from .models import Workspace, WorkspaceInvitation, WorkspaceRole
from .serializers import WorkspaceInvitationSerializer
from .views import _get_workspace


class WorkspaceInvitationListView(APIView):
    """
    GET  /api/workspaces/<slug>/invitations/  — list pending invitations
    POST /api/workspaces/<slug>/invitations/  — create email invite
    """

    def _require_admin(self, request, workspace):
        from tasks.services import AccessControlService
        if not request.user.has_elevated_access() and not AccessControlService.is_workspace_admin_or_owner(request.user, workspace):
            return Response({"detail": "Only Owner or Admin can manage invitations."}, status=403)
        return None

    def get(self, request, slug):
        workspace = _get_workspace(slug)
        err = self._require_admin(request, workspace)
        if err:
            return err
        invites = InvitationService.list_pending(workspace)
        return Response(WorkspaceInvitationSerializer(invites, many=True).data)

    def post(self, request, slug):
        workspace = _get_workspace(slug)
        err = self._require_admin(request, workspace)
        if err:
            return err
        email = request.data.get("email", "").strip()
        if not email:
            return Response({"detail": "email is required."}, status=400)
        role = request.data.get("role", WorkspaceRole.MEMBER)
        if role not in (WorkspaceRole.ADMIN, WorkspaceRole.MEMBER):
            return Response({"detail": "Invalid role."}, status=400)
        invite, _ = InvitationService.create_email_invite(workspace, email, role, request.user)
        return Response(WorkspaceInvitationSerializer(invite).data, status=201)


class WorkspaceInvitationDetailView(APIView):
    """
    DELETE /api/workspaces/<slug>/invitations/<id>/  — revoke invitation
    """

    def delete(self, request, slug, invite_id):
        workspace = _get_workspace(slug)
        from tasks.services import AccessControlService
        if not request.user.has_elevated_access() and not AccessControlService.is_workspace_admin_or_owner(request.user, workspace):
            return Response({"detail": "Only Owner or Admin can revoke invitations."}, status=403)
        invite = get_object_or_404(WorkspaceInvitation, pk=invite_id, workspace=workspace)
        try:
            InvitationService.revoke(invite, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(status=204)


class WorkspaceInviteLinkView(APIView):
    """
    POST /api/workspaces/<slug>/invite-links/  — create shareable invite link
    Returns the raw token exactly once.
    """

    def post(self, request, slug):
        workspace = _get_workspace(slug)
        from tasks.services import AccessControlService
        if not request.user.has_elevated_access() and not AccessControlService.is_workspace_admin_or_owner(request.user, workspace):
            return Response({"detail": "Only Owner or Admin can create invite links."}, status=403)
        role = request.data.get("role", WorkspaceRole.MEMBER)
        if role not in (WorkspaceRole.ADMIN, WorkspaceRole.MEMBER):
            return Response({"detail": "Invalid role."}, status=400)
        max_uses = request.data.get("max_uses")
        expires_at = request.data.get("expires_at")
        _, raw_token = InvitationService.create_invite_link(workspace, role, request.user, max_uses=max_uses, expires_at=expires_at)
        return Response({"token": raw_token}, status=201)


class InvitationAcceptView(APIView):
    """
    POST /api/invitations/accept/  — accept an invitation by token (auth required)
    """

    def post(self, request):
        token = request.data.get("token", "").strip()
        if not token:
            return Response({"detail": "token is required."}, status=400)
        try:
            workspace = InvitationService.accept(token, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        from .serializers import WorkspaceSerializer
        return Response(WorkspaceSerializer(workspace).data)


class MyInvitationsView(APIView):
    """
    GET /api/invitations/me/  — pending email invitations for the current user's email
    """

    def get(self, request):
        from django.utils import timezone
        from .models import WorkspaceInvitationKind
        invites = WorkspaceInvitation.objects.filter(
            kind=WorkspaceInvitationKind.EMAIL,
            email__iexact=request.user.email,
            accepted_at__isnull=True,
            revoked_at__isnull=True,
        ).exclude(expires_at__lt=timezone.now()).select_related("workspace", "invited_by")
        return Response(WorkspaceInvitationSerializer(invites, many=True).data)
