import hashlib
import secrets

from django.db import models, transaction
from django.utils import timezone

from users.models import NotificationType, User

from .models import (
    InvitationKind,
    Workspace,
    WorkspaceInvitation,
    WorkspaceRole,
)


class InvitationService:
    @staticmethod
    @transaction.atomic
    def create_email_invite(
        workspace: Workspace,
        email: str,
        role: str = WorkspaceRole.MEMBER,
        invited_by: User | None = None,
    ) -> tuple[WorkspaceInvitation, str]:
        raw_token = secrets.token_hex(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        invite = WorkspaceInvitation.objects.create(
            workspace=workspace,
            kind=InvitationKind.EMAIL,
            email=email,
            token_hash=token_hash,
            role_to_grant=role,
            invited_by=invited_by,
            expires_at=timezone.now() + timezone.timedelta(days=7),
            max_uses=1,
        )

        def _send():
            from users.tasks import send_workspace_invite_email
            send_workspace_invite_email.delay(str(invite.pk), raw_token)

        transaction.on_commit(_send)
        return invite, raw_token

    @staticmethod
    @transaction.atomic
    def create_invite_link(
        workspace: Workspace,
        role: str = WorkspaceRole.MEMBER,
        invited_by: User | None = None,
        max_uses: int | None = None,
        expires_at=None,
    ) -> tuple[WorkspaceInvitation, str]:
        raw_token = secrets.token_hex(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        invite = WorkspaceInvitation.objects.create(
            workspace=workspace,
            kind=InvitationKind.LINK,
            token_hash=token_hash,
            role_to_grant=role,
            invited_by=invited_by,
            expires_at=expires_at,
            max_uses=max_uses,
        )
        return invite, raw_token

    @staticmethod
    @transaction.atomic
    def accept(raw_token: str, user: User) -> WorkspaceInvitation:
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        try:
            invite = WorkspaceInvitation.objects.select_related("workspace").get(
                token_hash=token_hash
            )
        except WorkspaceInvitation.DoesNotExist:
            raise ValueError("Invalid or expired invitation token.")

        now = timezone.now()
        if invite.revoked_at is not None:
            raise ValueError("This invitation has been revoked.")
        if invite.expires_at is not None and invite.expires_at < now:
            raise ValueError("This invitation has expired.")
        if invite.max_uses is not None and invite.use_count >= invite.max_uses:
            raise ValueError("This invitation has reached its maximum number of uses.")
        if invite.kind == InvitationKind.EMAIL and invite.email and invite.email != user.email:
            raise ValueError("This invitation was sent to a different email address.")

        from .services import WorkspaceService
        WorkspaceService.add_member(
            workspace=invite.workspace,
            user=user,
            role=invite.role_to_grant,
            invited_by=invite.invited_by,
        )

        invite.use_count += 1
        if invite.kind == InvitationKind.EMAIL:
            invite.accepted_at = now
            invite.accepted_by = user
            invite.revoked_at = now  # single-use: immediately close
        invite.save(update_fields=["use_count", "accepted_at", "accepted_by", "revoked_at"])

        if invite.invited_by:
            from users.services import NotificationService
            NotificationService.create(
                recipient=invite.invited_by,
                notification_type=NotificationType.INVITED,
                message=f"{user.display_name} accepted your invitation to '{invite.workspace.name}'",
                actor=user,
            )
        return invite

    @staticmethod
    @transaction.atomic
    def revoke(invite: WorkspaceInvitation, actor: User) -> WorkspaceInvitation:
        from tasks.services import AccessControlService
        if not AccessControlService.is_workspace_admin_or_owner(actor, invite.workspace):
            raise ValueError("Only workspace Owner or Admin can revoke invitations.")
        if invite.revoked_at is not None:
            raise ValueError("Invitation is already revoked.")
        invite.revoked_at = timezone.now()
        invite.save(update_fields=["revoked_at"])
        return invite

    @staticmethod
    def list_pending(workspace: Workspace):
        now = timezone.now()
        return WorkspaceInvitation.objects.filter(
            workspace=workspace,
            revoked_at__isnull=True,
            accepted_at__isnull=True,
        ).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        )
