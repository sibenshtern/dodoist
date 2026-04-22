from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .invitations import InvitationService
from .models import Workspace, WorkspaceInvitation, WorkspaceRole
from .serializers import WorkspaceInvitationSerializer


def _get_workspace(slug: str) -> Workspace:
    return get_object_or_404(Workspace.objects.select_related("owner"), slug=slug)


def _require_admin_or_owner(workspace, user):
    from tasks.services import AccessControlService
    if not user.has_elevated_access() and not AccessControlService.is_workspace_admin_or_owner(user, workspace):
        return Response({"detail": "Only Owner or Admin can manage invitations."}, status=403)
    return None


class WorkspaceInvitationListCreateView(APIView):
    """
    GET  /api/workspaces/<slug>/invitations/ — list pending invitations
    POST /api/workspaces/<slug>/invitations/ — create email invitation
    """

    def get(self, request, slug):
        workspace = _get_workspace(slug)
        err = _require_admin_or_owner(workspace, request.user)
        if err:
            return err
        invites = InvitationService.list_pending(workspace).select_related("invited_by")
        return Response(WorkspaceInvitationSerializer(invites, many=True).data)

    def post(self, request, slug):
        workspace = _get_workspace(slug)
        err = _require_admin_or_owner(workspace, request.user)
        if err:
            return err
        email = request.data.get("email", "").strip()
        if not email:
            return Response({"detail": "email is required."}, status=400)
        role = request.data.get("role", WorkspaceRole.MEMBER)
        if role not in (WorkspaceRole.ADMIN, WorkspaceRole.MEMBER):
            return Response({"detail": "role must be ADMIN or MEMBER."}, status=400)
        try:
            invite, _ = InvitationService.create_email_invite(
                workspace=workspace,
                email=email,
                role=role,
                invited_by=request.user,
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(WorkspaceInvitationSerializer(invite).data, status=201)


class WorkspaceInvitationDetailView(APIView):
    """DELETE /api/workspaces/<slug>/invitations/<pk>/ — revoke invitation"""

    def delete(self, request, slug, pk):
        workspace = _get_workspace(slug)
        err = _require_admin_or_owner(workspace, request.user)
        if err:
            return err
        invite = get_object_or_404(WorkspaceInvitation, pk=pk, workspace=workspace)
        try:
            InvitationService.revoke(invite, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(status=204)


class WorkspaceInviteLinkView(APIView):
    """POST /api/workspaces/<slug>/invite-links/ — generate a shareable invite link"""

    def post(self, request, slug):
        workspace = _get_workspace(slug)
        err = _require_admin_or_owner(workspace, request.user)
        if err:
            return err
        role = request.data.get("role", WorkspaceRole.MEMBER)
        if role not in (WorkspaceRole.ADMIN, WorkspaceRole.MEMBER):
            return Response({"detail": "role must be ADMIN or MEMBER."}, status=400)
        max_uses = request.data.get("max_uses")
        expires_at = request.data.get("expires_at")
        if expires_at:
            from django.utils.dateparse import parse_datetime
            expires_at = parse_datetime(expires_at)
            if not expires_at:
                return Response({"detail": "Invalid expires_at format."}, status=400)
        _, raw_token = InvitationService.create_invite_link(
            workspace=workspace,
            role=role,
            invited_by=request.user,
            max_uses=int(max_uses) if max_uses is not None else None,
            expires_at=expires_at,
        )
        return Response({"token": raw_token}, status=201)


class InvitationAcceptView(APIView):
    """POST /api/invitations/accept/ — accept a workspace invitation (auth required)"""

    def post(self, request):
        from .serializers import WorkspaceSerializer
        token = request.data.get("token", "").strip()
        if not token:
            return Response({"detail": "token is required."}, status=400)
        try:
            invite = InvitationService.accept(token, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(WorkspaceSerializer(invite.workspace).data)


class MyInvitationsView(APIView):
    """GET /api/invitations/me/ — pending email invitations sent to the current user's email"""

    def get(self, request):
        from django.utils import timezone
        from .models import InvitationKind
        now = timezone.now()
        invites = WorkspaceInvitation.objects.filter(
            kind=InvitationKind.EMAIL,
            email=request.user.email,
            revoked_at__isnull=True,
            accepted_at__isnull=True,
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        ).select_related("workspace", "invited_by")
        return Response(WorkspaceInvitationSerializer(invites, many=True).data)
