import hashlib
import secrets

from django.db import transaction
from django.utils import timezone

from users.models import NotificationType, User

from .models import (
    Workspace,
    WorkspaceInvitation,
    WorkspaceInvitationKind,
    WorkspaceRole,
)
from .services import WorkspaceService


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class InvitationService:
    @staticmethod
    @transaction.atomic
    def create_email_invite(
        workspace: Workspace,
        email: str,
        role: str,
        invited_by: User,
    ) -> tuple[WorkspaceInvitation, str]:
        raw_token = secrets.token_hex(32)
        invite = WorkspaceInvitation.objects.create(
            workspace=workspace,
            kind=WorkspaceInvitationKind.EMAIL,
            email=email.lower().strip(),
            token_hash=_hash_token(raw_token),
            role_to_grant=role,
            invited_by=invited_by,
            expires_at=timezone.now() + timezone.timedelta(days=7),
            max_uses=1,
        )

        invite_id = str(invite.pk)

        def _dispatch():
            from users.tasks import send_workspace_invite_email
            send_workspace_invite_email.delay(invite_id, raw_token)

        transaction.on_commit(_dispatch)
        return invite, raw_token

    @staticmethod
    @transaction.atomic
    def create_invite_link(
        workspace: Workspace,
        role: str,
        invited_by: User,
        max_uses: int | None = None,
        expires_at=None,
    ) -> tuple[WorkspaceInvitation, str]:
        raw_token = secrets.token_hex(32)
        invite = WorkspaceInvitation.objects.create(
            workspace=workspace,
            kind=WorkspaceInvitationKind.LINK,
            token_hash=_hash_token(raw_token),
            role_to_grant=role,
            invited_by=invited_by,
            expires_at=expires_at,
            max_uses=max_uses,
        )
        return invite, raw_token

    @staticmethod
    @transaction.atomic
    def accept(raw_token: str, user: User) -> Workspace:
        token_hash = _hash_token(raw_token)
        try:
            invite = WorkspaceInvitation.objects.select_related("workspace", "invited_by").get(
                token_hash=token_hash
            )
        except WorkspaceInvitation.DoesNotExist:
            raise ValueError("INVALID_TOKEN")

        if invite.is_revoked():
            raise ValueError("INVITE_REVOKED")
        if invite.is_expired():
            raise ValueError("INVITE_EXPIRED")
        if invite.uses_exhausted():
            raise ValueError("INVITE_EXHAUSTED")
        if invite.kind == WorkspaceInvitationKind.EMAIL and invite.email:
            if invite.email.lower() != user.email.lower():
                raise ValueError("INVITE_EMAIL_MISMATCH")

        WorkspaceService.add_member(
            workspace=invite.workspace,
            user=user,
            role=invite.role_to_grant,
            invited_by=invite.invited_by,
        )

        if invite.kind == WorkspaceInvitationKind.EMAIL:
            invite.accepted_at = timezone.now()
            invite.accepted_by = user
            invite.revoked_at = timezone.now()  # single-use: consume it
        else:
            invite.use_count += 1
            invite.accepted_at = invite.accepted_at or timezone.now()
            invite.accepted_by = invite.accepted_by or user

        invite.save()

        if invite.invited_by and invite.invited_by.pk != user.pk:
            from users.services import NotificationService
            NotificationService.create(
                recipient=invite.invited_by,
                notification_type=NotificationType.INVITED,
                message=(
                    f"{user.display_name} accepted your invitation to "
                    f"'{invite.workspace.name}'"
                ),
                actor=user,
            )

        return invite.workspace

    @staticmethod
    @transaction.atomic
    def revoke(invite: WorkspaceInvitation, actor: User) -> WorkspaceInvitation:
        if invite.is_revoked():
            raise ValueError("Invitation is already revoked.")
        invite.revoked_at = timezone.now()
        invite.save(update_fields=["revoked_at"])
        return invite

    @staticmethod
    def list_pending(workspace: Workspace):
        now = timezone.now()
        return WorkspaceInvitation.objects.filter(
            workspace=workspace,
            accepted_at__isnull=True,
            revoked_at__isnull=True,
        ).exclude(
            expires_at__lt=now
        ).select_related("invited_by").order_by("-created_at")
