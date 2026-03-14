import pytest

from projects.models import (
    Board,
    BoardColumn,
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
from projects.services import ProjectService, SprintService, WorkspaceService
from users.models import GlobalRole, User
from users.services import UserService


@pytest.fixture
def user(db):
    return UserService.register(
        email="alice@example.com", password="pass123", display_name="Alice"
    )


@pytest.fixture
def other_user(db):
    return UserService.register(
        email="bob@example.com", password="pass123", display_name="Bob"
    )


@pytest.fixture
def workspace(user):
    return WorkspaceService.create_workspace(owner=user, name="Acme", slug="acme")


@pytest.fixture
def project(workspace, user):
    return ProjectService.create_project(
        workspace=workspace, creator=user, name="Alpha", key="ALP"
    )


@pytest.fixture
def scrum_project(workspace, user):
    return ProjectService.create_project(
        workspace=workspace, creator=user, name="Scrum", key="SCR",
        project_type=ProjectType.SCRUM,
    )


# ---------------------------------------------------------------------------
# WorkspaceService
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkspaceService:
    def test_create_personal_workspace(self, user):
        ws = WorkspaceService.create_personal_workspace(user)
        assert ws.is_personal is True
        assert ws.owner_id == user.pk
        assert WorkspaceMember.objects.filter(workspace=ws, user=user).exists()

    def test_create_workspace(self, user):
        ws = WorkspaceService.create_workspace(owner=user, name="TestCo", slug="testco")
        assert ws.slug == "testco"
        assert WorkspaceMember.objects.filter(workspace=ws, user=user).exists()

    def test_create_workspace_auto_slug(self, user):
        ws = WorkspaceService.create_workspace(owner=user, name="My Company")
        assert " " not in ws.slug

    def test_duplicate_slug_raises(self, user):
        WorkspaceService.create_workspace(owner=user, name="First", slug="taken")
        with pytest.raises(ValueError, match="already taken"):
            WorkspaceService.create_workspace(owner=user, name="Second", slug="taken")

    def test_add_member(self, workspace, other_user):
        member = WorkspaceService.add_member(workspace, other_user)
        assert member.workspace_id == workspace.pk

    def test_add_member_idempotent(self, workspace, user):
        m1 = WorkspaceService.add_member(workspace, user)
        m2 = WorkspaceService.add_member(workspace, user)
        assert m1.pk == m2.pk

    def test_remove_member(self, workspace, other_user):
        WorkspaceService.add_member(workspace, other_user)
        WorkspaceService.remove_member(workspace, other_user)
        assert not WorkspaceMember.objects.filter(workspace=workspace, user=other_user).exists()

    def test_remove_owner_raises(self, workspace, user):
        with pytest.raises(ValueError, match="Cannot remove the workspace owner"):
            WorkspaceService.remove_member(workspace, user)


# ---------------------------------------------------------------------------
# ProjectService
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProjectService:
    def test_create_project_fields(self, workspace, user):
        p = ProjectService.create_project(workspace=workspace, creator=user, name="Beta", key="BETA")
        assert p.name == "Beta"
        assert p.key == "BETA"
        assert p.status == ProjectStatus.ACTIVE
        assert p.workspace_id == workspace.pk

    def test_creator_added_as_po(self, project, user):
        membership = ProjectMember.objects.get(project=project, user=user)
        assert membership.role == ProjectRole.PO

    def test_default_board_created(self, project):
        assert Board.objects.filter(project=project, is_default=True).exists()

    def test_default_board_has_five_columns(self, project):
        board = Board.objects.get(project=project, is_default=True)
        assert board.columns.count() == 5

    def test_default_board_column_order(self, project):
        board = Board.objects.get(project=project, is_default=True)
        statuses = list(board.columns.values_list("status_mapping", flat=True))
        assert statuses == [
            TaskStatus.BACKLOG,
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
            TaskStatus.IN_REVIEW,
            TaskStatus.DONE,
        ]

    def test_duplicate_key_raises(self, workspace, user, project):
        with pytest.raises(ValueError, match="already used"):
            ProjectService.create_project(workspace=workspace, creator=user, name="P2", key="ALP")

    def test_non_member_cannot_create_project(self, workspace, other_user):
        with pytest.raises(ValueError, match="workspace member"):
            ProjectService.create_project(
                workspace=workspace, creator=other_user, name="P", key="P"
            )

    def test_elevated_user_can_create_without_membership(self, workspace, db):
        ga = User.objects.create_user(
            email="ga@example.com", password="p", display_name="GA",
            global_role=GlobalRole.GA,
        )
        p = ProjectService.create_project(workspace=workspace, creator=ga, name="GA", key="GA")
        assert p.pk is not None

    def test_archive_project(self, project):
        result = ProjectService.archive_project(project)
        assert result.status == ProjectStatus.ARCHIVED
        assert result.archived_at is not None

    def test_archive_deleted_project_raises(self, project):
        ProjectService.delete_project(project)
        with pytest.raises(ValueError, match="Cannot archive a deleted project"):
            ProjectService.archive_project(project)

    def test_archive_already_archived_raises(self, project):
        ProjectService.archive_project(project)
        with pytest.raises(ValueError, match="already archived"):
            ProjectService.archive_project(project)

    def test_restore_project(self, project):
        ProjectService.archive_project(project)
        result = ProjectService.restore_project(project)
        assert result.status == ProjectStatus.ACTIVE
        assert result.archived_at is None

    def test_restore_active_project_raises(self, project):
        with pytest.raises(ValueError, match="Only archived projects"):
            ProjectService.restore_project(project)

    def test_delete_project(self, project):
        result = ProjectService.delete_project(project)
        assert result.status == ProjectStatus.DELETED

    def test_add_member(self, workspace, project, other_user):
        WorkspaceService.add_member(workspace, other_user)
        member = ProjectService.add_member(project, other_user, ProjectRole.DEV)
        assert member.role == ProjectRole.DEV

    def test_add_member_updates_existing_role(self, workspace, project, user):
        member = ProjectService.add_member(project, user, ProjectRole.PM)
        assert member.role == ProjectRole.PM

    def test_add_member_invalid_role_raises(self, workspace, project, other_user):
        WorkspaceService.add_member(workspace, other_user)
        with pytest.raises(ValueError, match="Invalid role"):
            ProjectService.add_member(project, other_user, "OWNER")

    def test_add_member_non_workspace_member_raises(self, project, other_user):
        with pytest.raises(ValueError, match="workspace member first"):
            ProjectService.add_member(project, other_user, ProjectRole.DEV)

    def test_remove_member(self, workspace, project, other_user):
        WorkspaceService.add_member(workspace, other_user)
        ProjectService.add_member(project, other_user, ProjectRole.DEV)
        ProjectService.remove_member(project, other_user)
        assert not ProjectMember.objects.filter(project=project, user=other_user).exists()

    def test_remove_po_raises(self, project, user):
        with pytest.raises(ValueError, match="Cannot remove the project owner"):
            ProjectService.remove_member(project, user)


# ---------------------------------------------------------------------------
# SprintService
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSprintService:
    def test_create_sprint(self, scrum_project, user):
        sprint = SprintService.create_sprint(project=scrum_project, creator=user, name="Sprint 1")
        assert sprint.name == "Sprint 1"
        assert sprint.status == SprintStatus.PLANNED

    def test_create_sprint_on_non_scrum_raises(self, project, user):
        with pytest.raises(ValueError, match="only available for Scrum"):
            SprintService.create_sprint(project=project, creator=user, name="S1")

    def test_start_sprint(self, scrum_project, user):
        sprint = SprintService.create_sprint(project=scrum_project, creator=user, name="S1")
        result = SprintService.start_sprint(sprint)
        assert result.status == SprintStatus.ACTIVE

    def test_start_non_planned_sprint_raises(self, scrum_project, user):
        sprint = SprintService.create_sprint(project=scrum_project, creator=user, name="S1")
        SprintService.start_sprint(sprint)
        with pytest.raises(ValueError, match="Only planned sprints"):
            SprintService.start_sprint(sprint)

    def test_only_one_active_sprint_per_project(self, scrum_project, user):
        s1 = SprintService.create_sprint(project=scrum_project, creator=user, name="S1")
        s2 = SprintService.create_sprint(project=scrum_project, creator=user, name="S2")
        SprintService.start_sprint(s1)
        with pytest.raises(ValueError, match="already active"):
            SprintService.start_sprint(s2)

    def test_complete_sprint(self, scrum_project, user):
        sprint = SprintService.create_sprint(project=scrum_project, creator=user, name="S1")
        SprintService.start_sprint(sprint)
        result = SprintService.complete_sprint(sprint)
        assert result.status == SprintStatus.COMPLETED
        assert result.completed_at is not None

    def test_complete_non_active_sprint_raises(self, scrum_project, user):
        sprint = SprintService.create_sprint(project=scrum_project, creator=user, name="S1")
        with pytest.raises(ValueError, match="Only active sprints"):
            SprintService.complete_sprint(sprint)
