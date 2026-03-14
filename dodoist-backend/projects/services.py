import re
import uuid

from django.db import transaction
from django.utils import timezone

from users.models import User

from .models import (
    Board,
    BoardColumn,
    BoardType,
    Project,
    ProjectMember,
    ProjectRole,
    ProjectStatus,
    ProjectType,
    Sprint,
    SprintStatus,
    TaskStatus,
    Workspace,
    WorkspaceMember,
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


# ---------------------------------------------------------------------------
# WorkspaceService
# ---------------------------------------------------------------------------

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
        WorkspaceMember.objects.create(workspace=ws, user=user)
        return ws

    @staticmethod
    @transaction.atomic
    def create_workspace(owner: User, name: str, slug: str | None = None) -> Workspace:
        slug = slug or _unique_slug(name)
        if Workspace.objects.filter(slug=slug).exists():
            raise ValueError(f"Slug '{slug}' is already taken.")
        ws = Workspace.objects.create(slug=slug, name=name, owner=owner)
        WorkspaceMember.objects.create(workspace=ws, user=owner)
        return ws

    @staticmethod
    def add_member(workspace: Workspace, user: User) -> WorkspaceMember:
        member, _ = WorkspaceMember.objects.get_or_create(workspace=workspace, user=user)
        return member

    @staticmethod
    def remove_member(workspace: Workspace, user: User) -> None:
        if workspace.owner_id == user.pk:
            raise ValueError("Cannot remove the workspace owner.")
        WorkspaceMember.objects.filter(workspace=workspace, user=user).delete()


# ---------------------------------------------------------------------------
# ProjectService
# ---------------------------------------------------------------------------

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
    def add_member(project: Project, user: User, role: str) -> ProjectMember:
        if role not in ProjectRole.values:
            raise ValueError(f"Invalid role '{role}'. Choices: {ProjectRole.values}")
        if not user.has_elevated_access():
            ws_member = WorkspaceMember.objects.filter(
                workspace=project.workspace, user=user
            ).exists()
            if not ws_member:
                raise ValueError("User must be a workspace member first.")
        member, _ = ProjectMember.objects.update_or_create(
            project=project, user=user, defaults={"role": role}
        )
        return member

    @staticmethod
    def remove_member(project: Project, user: User) -> None:
        membership = ProjectMember.objects.filter(project=project, user=user).first()
        if membership and membership.role == ProjectRole.PO:
            raise ValueError("Cannot remove the project owner.")
        ProjectMember.objects.filter(project=project, user=user).delete()


# ---------------------------------------------------------------------------
# SprintService
# ---------------------------------------------------------------------------

class SprintService:
    @staticmethod
    def create_sprint(project: Project, creator: User, name: str, goal: str = "") -> Sprint:
        if project.type != ProjectType.SCRUM:
            raise ValueError("Sprints are only available for Scrum projects.")
        return Sprint.objects.create(project=project, created_by=creator, name=name, goal=goal)

    @staticmethod
    def start_sprint(sprint: Sprint) -> Sprint:
        if sprint.status != SprintStatus.PLANNED:
            raise ValueError("Only planned sprints can be started.")
        if Sprint.objects.filter(project=sprint.project, status=SprintStatus.ACTIVE).exists():
            raise ValueError("A sprint is already active in this project.")
        sprint.status = SprintStatus.ACTIVE
        sprint.save(update_fields=["status", "updated_at"])
        return sprint

    @staticmethod
    def complete_sprint(sprint: Sprint) -> Sprint:
        if sprint.status != SprintStatus.ACTIVE:
            raise ValueError("Only active sprints can be completed.")
        sprint.status = SprintStatus.COMPLETED
        sprint.completed_at = timezone.now()
        sprint.save(update_fields=["status", "completed_at", "updated_at"])
        return sprint
