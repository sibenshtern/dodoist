import re
import uuid

from django.db import transaction
from django.utils import timezone

from users.models import NotificationType, User

from .models import (
    Board,
    BoardColumn,
    BoardType,
    InvitationKind,
    Project,
    ProjectMember,
    ProjectRole,
    ProjectStatus,
    ProjectType,
    Sprint,
    SprintStatus,
    TaskStatus,
    Workspace,
    WorkspaceInvitation,
    WorkspaceMember,
    WorkspacePlan,
    WorkspaceRole,
)

_DEFAULT_COLUMNS = [
    ("Backlog",     TaskStatus.BACKLOG),
    ("To Do",       TaskStatus.TODO),
    ("In Progress", TaskStatus.IN_PROGRESS),
    ("In Review",   TaskStatus.IN_REVIEW),
    ("Done",        TaskStatus.DONE),
]


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug or uuid.uuid4().hex[:8]


def _unique_slug(base: str) -> str:
    slug = _slugify(base)
    candidate = slug
    n = 1
    while Workspace.objects.filter(slug=candidate).exists():
        candidate = f"{slug}-{n}"
        n += 1
    return candidate


def _ws_log(actor: User, workspace: Workspace, action: str, old=None, new=None) -> None:
    from tasks.models import ActivityEntityType, ActivityLog
    ActivityLog.objects.create(
        entity_type=ActivityEntityType.WORKSPACE,
        entity_id=workspace.pk,
        actor=actor,
        action=action,
        old_value=old,
        new_value=new,
        project=None,
    )


class WorkspaceService:
    @staticmethod
    @transaction.atomic
    def create_personal_workspace(user: User) -> Workspace:
        slug = _unique_slug(f"{user.display_name}-personal")
        ws = Workspace.objects.create(
            slug=slug,
            name=f"{user.display_name}'s workspace",
            owner=user,
            is_personal=True,
        )
        WorkspaceMember.objects.create(workspace=ws, user=user, role=WorkspaceRole.OWNER)
        if user.active_workspace_id is None:
            user.active_workspace = ws
            user.save(update_fields=["active_workspace"])
        return ws

    @staticmethod
    @transaction.atomic
    def create_team_workspace(
        owner: User,
        name: str,
        slug: str | None = None,
        description: str = "",
    ) -> Workspace:
        slug = slug or _unique_slug(name)
        if Workspace.objects.filter(slug=slug).exists():
            raise ValueError(f"Slug '{slug}' is already taken.")
        ws = Workspace.objects.create(
            slug=slug, name=name, owner=owner, description=description
        )
        WorkspaceMember.objects.create(workspace=ws, user=owner, role=WorkspaceRole.OWNER)
        return ws

    @staticmethod
    @transaction.atomic
    def create_team_workspace(
        owner: User,
        name: str,
        slug: str | None = None,
        description: str = "",
        plan: str = "",  # kept for backward-compat; no longer applied
    ) -> Workspace:
        """Backward-compatible alias for create_team_workspace; plan param is accepted but ignored in logic."""
        slug = slug or _unique_slug(name)
        if Workspace.objects.filter(slug=slug).exists():
            raise ValueError(f"Slug '{slug}' is already taken.")
        ws = Workspace.objects.create(
            slug=slug, name=name, owner=owner, description=description
        )
        WorkspaceMember.objects.create(workspace=ws, user=owner, role=WorkspaceRole.OWNER)
        return ws

    # Keep old name as alias so existing callers don't break.
    create_workspace = create_team_workspace

    @staticmethod
    @transaction.atomic
    def add_member(
        workspace: Workspace,
        user: User,
        role: str = WorkspaceRole.MEMBER,
        invited_by: User | None = None,
    ) -> WorkspaceMember:
        if role == WorkspaceRole.OWNER:
            raise ValueError("Cannot assign OWNER role via add_member. Use transfer_ownership.")
        defaults = {"role": role}
        if invited_by is not None:
            defaults["invited_by"] = invited_by
        member, _ = WorkspaceMember.objects.update_or_create(
            workspace=workspace, user=user, defaults=defaults
        )
        return member

    @staticmethod
    @transaction.atomic
    def remove_member(workspace: Workspace, user: User) -> int:
        if workspace.owner_id == user.pk:
            raise ValueError("Cannot remove the workspace owner. Transfer ownership first.")
        WorkspaceMember.objects.filter(workspace=workspace, user=user).delete()
        deleted, _ = ProjectMember.objects.filter(
            project__workspace=workspace, user=user
        ).delete()
        _ws_log(user, workspace, "member_removed", new={"user_id": str(user.pk)})
        return deleted

    @staticmethod
    @transaction.atomic
    def change_role(
        workspace: Workspace, user: User, new_role: str, actor: User
    ) -> WorkspaceMember:
        if new_role == WorkspaceRole.OWNER:
            raise ValueError("Cannot promote to OWNER via change_role. Use transfer_ownership.")
        if new_role not in WorkspaceRole.values:
            raise ValueError(f"Invalid role '{new_role}'.")

        actor_member = WorkspaceMember.objects.filter(workspace=workspace, user=actor).first()
        if actor_member is None or actor_member.role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
            raise ValueError("Only workspace Owner or Admin can change member roles.")

        target_member = WorkspaceMember.objects.filter(workspace=workspace, user=user).first()
        if target_member is None:
            raise ValueError("User is not a member of this workspace.")
        if target_member.role == WorkspaceRole.OWNER:
            raise ValueError("Cannot demote the workspace Owner.")
        if actor_member.role == WorkspaceRole.ADMIN and target_member.role == WorkspaceRole.ADMIN:
            raise ValueError("Admins cannot change the role of other Admins.")

        old_role = target_member.role
        target_member.role = new_role
        target_member.save(update_fields=["role"])
        _ws_log(actor, workspace, "role_changed",
                old={"user_id": str(user.pk), "role": old_role},
                new={"user_id": str(user.pk), "role": new_role})
        return target_member

    @staticmethod
    @transaction.atomic
    def transfer_ownership(workspace: Workspace, new_owner: User, actor: User) -> Workspace:
        if workspace.owner_id != actor.pk:
            raise ValueError("Only the current Owner can transfer ownership.")
        if workspace.owner_id == new_owner.pk:
            raise ValueError("New owner is already the current owner.")

        new_owner_member = WorkspaceMember.objects.filter(workspace=workspace, user=new_owner).first()
        if new_owner_member is None:
            raise ValueError("New owner must be a member of the workspace.")

        old_owner_member = WorkspaceMember.objects.filter(workspace=workspace, user=actor).first()

        workspace.owner = new_owner
        workspace.save(update_fields=["owner"])
        new_owner_member.role = WorkspaceRole.OWNER
        new_owner_member.save(update_fields=["role"])
        if old_owner_member:
            old_owner_member.role = WorkspaceRole.ADMIN
            old_owner_member.save(update_fields=["role"])

        _ws_log(actor, workspace, "ownership_transferred",
                old={"owner_id": str(actor.pk)},
                new={"owner_id": str(new_owner.pk)})
        return workspace

    @staticmethod
    @transaction.atomic
    def soft_delete(workspace: Workspace, actor: User) -> Workspace:
        if workspace.owner_id != actor.pk:
            raise ValueError("Only the workspace Owner can delete a workspace.")
        if workspace.is_personal:
            raise ValueError("Personal workspaces cannot be deleted.")
        if workspace.deleted_at is not None:
            raise ValueError("Workspace is already scheduled for deletion.")

        now = timezone.now()
        workspace.deleted_at = now
        workspace.deleted_by = actor
        workspace.delete_scheduled_for = now + timezone.timedelta(days=30)
        workspace.save(update_fields=["deleted_at", "deleted_by", "delete_scheduled_for"])
        _ws_log(actor, workspace, "soft_deleted",
                new={"delete_scheduled_for": workspace.delete_scheduled_for.isoformat()})
        return workspace

    @staticmethod
    @transaction.atomic
    def restore(workspace: Workspace, actor: User) -> Workspace:
        if workspace.owner_id != actor.pk:
            raise ValueError("Only the workspace Owner can restore a workspace.")
        if workspace.deleted_at is None:
            raise ValueError("Workspace is not scheduled for deletion.")
        if workspace.delete_scheduled_for and workspace.delete_scheduled_for <= timezone.now():
            raise ValueError("Grace period has expired; workspace cannot be restored.")

        workspace.deleted_at = None
        workspace.deleted_by = None
        workspace.delete_scheduled_for = None
        workspace.save(update_fields=["deleted_at", "deleted_by", "delete_scheduled_for"])
        _ws_log(actor, workspace, "restored")
        return workspace

    @staticmethod
    @transaction.atomic
    def leave(workspace: Workspace, user: User) -> int:
        if workspace.owner_id == user.pk:
            raise ValueError("Owner cannot leave the workspace. Transfer ownership first.")
        return WorkspaceService.remove_member(workspace, user)


class ProjectService:
    @staticmethod
    @transaction.atomic
    def create_project(
        workspace: Workspace,
        creator: User,
        name: str,
        key: str,
        project_type: str = ProjectType.KANBAN,
        is_private: bool = False,
        description: str = "",
        color: str = "",
    ) -> Project:
        if not creator.has_elevated_access():
            if not WorkspaceMember.objects.filter(workspace=workspace, user=creator).exists():
                raise ValueError("Creator must be a workspace member.")

        if Project.objects.filter(workspace=workspace, key=key).exists():
            raise ValueError(f"Key '{key}' is already used in this workspace.")

        project = Project.objects.create(
            workspace=workspace,
            name=name,
            key=key.upper(),
            type=project_type,
            is_private=is_private,
            created_by=creator,
            description=description,
            color=color,
        )

        ProjectMember.objects.create(project=project, user=creator, role=ProjectRole.PO)

        board_type = BoardType.SCRUM if project_type == ProjectType.SCRUM else BoardType.KANBAN
        board = Board.objects.create(
            project=project,
            name="Main Board",
            type=board_type,
            is_default=True,
            created_by=creator,
        )
        for pos, (col_name, status) in enumerate(_DEFAULT_COLUMNS):
            BoardColumn.objects.create(
                board=board, name=col_name, status_mapping=status, position=pos
            )

        return project

    @staticmethod
    def archive_project(project: Project) -> Project:
        if project.status == ProjectStatus.DELETED:
            raise ValueError("Cannot archive a deleted project.")
        if project.status == ProjectStatus.ARCHIVED:
            raise ValueError("Project is already archived.")
        project.status = ProjectStatus.ARCHIVED
        project.archived_at = timezone.now()
        project.save(update_fields=["status", "archived_at", "updated_at"])
        return project

    @staticmethod
    def restore_project(project: Project) -> Project:
        if project.status != ProjectStatus.ARCHIVED:
            raise ValueError("Only archived projects can be restored.")
        project.status = ProjectStatus.ACTIVE
        project.archived_at = None
        project.save(update_fields=["status", "archived_at", "updated_at"])
        return project

    @staticmethod
    def delete_project(project: Project) -> Project:
        project.status = ProjectStatus.DELETED
        project.save(update_fields=["status", "updated_at"])
        return project

    @staticmethod
    @transaction.atomic
    def add_member(project: Project, user: User, role: str, added_by: User | None = None) -> ProjectMember:
        if role not in ProjectRole.values:
            raise ValueError(f"Invalid role '{role}'. Choices: {ProjectRole.values}")
        if not user.has_elevated_access():
            ws_member = WorkspaceMember.objects.filter(
                workspace=project.workspace, user=user
            ).exists()
            if not ws_member:
                raise ValueError("User must be a workspace member first.")
        member, created = ProjectMember.objects.update_or_create(
            project=project, user=user, defaults={"role": role}
        )
        if added_by and added_by.pk != user.pk:
            from users.services import NotificationService
            if created:
                NotificationService.create(
                    recipient=user,
                    notification_type=NotificationType.INVITED,
                    message=f"{added_by.display_name} invited you to project '{project.name}'",
                    actor=added_by,
                    project_id=project.pk,
                )
            else:
                NotificationService.create(
                    recipient=user,
                    notification_type=NotificationType.ROLE_CHANGED,
                    message=f"{added_by.display_name} changed your role to {role} in '{project.name}'",
                    actor=added_by,
                    project_id=project.pk,
                )
        return member

    @staticmethod
    @transaction.atomic
    def remove_member(project: Project, user: User) -> None:
        membership = ProjectMember.objects.filter(project=project, user=user).first()
        if membership and membership.role == ProjectRole.PO:
            raise ValueError("Cannot remove the project owner.")
        ProjectMember.objects.filter(project=project, user=user).delete()


class SprintService:
    @staticmethod
    @transaction.atomic
    def create_sprint(project: Project, creator: User, name: str, goal: str = "") -> Sprint:
        if project.type != ProjectType.SCRUM:
            raise ValueError("Sprints are only available for Scrum projects.")
        return Sprint.objects.create(project=project, created_by=creator, name=name, goal=goal)

    @staticmethod
    @transaction.atomic
    def start_sprint(sprint: Sprint) -> Sprint:
        if sprint.status != SprintStatus.PLANNED:
            raise ValueError("Only planned sprints can be started.")
        if Sprint.objects.filter(project=sprint.project, status=SprintStatus.ACTIVE).exists():
            raise ValueError("A sprint is already active in this project.")
        sprint.status = SprintStatus.ACTIVE
        sprint.save(update_fields=["status", "updated_at"])
        return sprint

    @staticmethod
    @transaction.atomic
    def complete_sprint(sprint: Sprint) -> Sprint:
        if sprint.status != SprintStatus.ACTIVE:
            raise ValueError("Only active sprints can be completed.")
        sprint.status = SprintStatus.COMPLETED
        sprint.completed_at = timezone.now()
        sprint.save(update_fields=["status", "completed_at", "updated_at"])
        return sprint
