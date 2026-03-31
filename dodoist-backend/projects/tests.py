import pytest
from rest_framework.test import APIClient

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
    WorkspacePlan,
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
def sa_user(db):
    return User.objects.create_user(
        email="sa@example.com", password="pass123", display_name="SA",
        global_role=GlobalRole.SA,
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


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


# ---------------------------------------------------------------------------
# WorkspaceService — description and plan params
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkspaceServiceCreate:
    def test_create_workspace_with_description(self, user):
        ws = WorkspaceService.create_workspace(owner=user, name="Acme", slug="acme-desc", description="Hello")
        assert ws.description == "Hello"

    def test_create_workspace_with_plan(self, user):
        ws = WorkspaceService.create_workspace(owner=user, name="Pro", slug="pro-ws", plan=WorkspacePlan.PRO)
        assert ws.plan == WorkspacePlan.PRO

    def test_create_workspace_default_plan_is_free(self, user):
        ws = WorkspaceService.create_workspace(owner=user, name="Free", slug="free-ws")
        assert ws.plan == WorkspacePlan.FREE

    def test_create_workspace_default_description_is_empty(self, user):
        ws = WorkspaceService.create_workspace(owner=user, name="Empty", slug="empty-ws")
        assert ws.description == ""


# ---------------------------------------------------------------------------
# API: WorkspaceListCreateView
# ---------------------------------------------------------------------------

WORKSPACES_URL = "/api/workspaces/"


@pytest.mark.django_db
class TestWorkspaceListCreateView:
    def test_list_returns_own_workspaces(self, auth_client, workspace):
        response = auth_client.get(WORKSPACES_URL)
        assert response.status_code == 200
        assert any(w["slug"] == "acme" for w in response.data)

    def test_list_excludes_other_users_workspaces(self, auth_client, other_user):
        other_ws = WorkspaceService.create_workspace(owner=other_user, name="Other", slug="other-ws")
        response = auth_client.get(WORKSPACES_URL)
        assert not any(w["slug"] == "other-ws" for w in response.data)

    def test_filter_is_personal_true(self, auth_client, user, workspace):
        WorkspaceService.create_personal_workspace(user)
        response = auth_client.get(WORKSPACES_URL + "?is_personal=true")
        assert response.status_code == 200
        assert response.data
        assert all(w["is_personal"] for w in response.data)

    def test_filter_is_personal_false(self, auth_client, user, workspace):
        WorkspaceService.create_personal_workspace(user)
        response = auth_client.get(WORKSPACES_URL + "?is_personal=false")
        assert response.status_code == 200
        assert all(not w["is_personal"] for w in response.data)

    def test_sa_sees_all_workspaces(self, api_client, sa_user, workspace):
        api_client.force_authenticate(user=sa_user)
        response = api_client.get(WORKSPACES_URL)
        assert response.status_code == 200
        assert any(w["slug"] == "acme" for w in response.data)

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(WORKSPACES_URL)
        assert response.status_code == 401

    def test_create_workspace(self, auth_client, user):
        response = auth_client.post(WORKSPACES_URL, {"name": "New Co", "slug": "new-co"})
        assert response.status_code == 201
        assert response.data["slug"] == "new-co"
        assert response.data["name"] == "New Co"
        assert response.data["owner"]["id"] == str(user.pk)

    def test_create_workspace_auto_slug(self, auth_client):
        response = auth_client.post(WORKSPACES_URL, {"name": "Auto Slug Corp"})
        assert response.status_code == 201
        assert " " not in response.data["slug"]

    def test_create_workspace_with_description_and_plan(self, auth_client):
        response = auth_client.post(WORKSPACES_URL, {
            "name": "Pro Co", "slug": "pro-co",
            "description": "A pro workspace", "plan": WorkspacePlan.PRO,
        })
        assert response.status_code == 201
        assert response.data["description"] == "A pro workspace"
        assert response.data["plan"] == WorkspacePlan.PRO

    def test_create_duplicate_slug_returns_400(self, auth_client, workspace):
        response = auth_client.post(WORKSPACES_URL, {"name": "Another", "slug": "acme"})
        assert response.status_code == 400

    def test_create_missing_name_returns_400(self, auth_client):
        response = auth_client.post(WORKSPACES_URL, {"slug": "no-name"})
        assert response.status_code == 400

    def test_unauthenticated_create_returns_401(self, api_client):
        response = api_client.post(WORKSPACES_URL, {"name": "X"})
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# API: WorkspaceDetailView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkspaceDetailView:
    def url(self, slug="acme"):
        return f"/api/workspaces/{slug}/"

    def test_member_can_retrieve(self, auth_client, workspace):
        response = auth_client.get(self.url())
        assert response.status_code == 200
        assert response.data["slug"] == "acme"

    def test_non_member_gets_404(self, api_client, workspace, other_user):
        api_client.force_authenticate(user=other_user)
        response = api_client.get(self.url())
        assert response.status_code == 404

    def test_sa_can_retrieve_any_workspace(self, api_client, sa_user, workspace):
        api_client.force_authenticate(user=sa_user)
        response = api_client.get(self.url())
        assert response.status_code == 200

    def test_nonexistent_workspace_returns_404(self, auth_client):
        response = auth_client.get(self.url("ghost"))
        assert response.status_code == 404

    def test_owner_can_patch_name(self, auth_client, workspace):
        response = auth_client.patch(self.url(), {"name": "Acme Updated"})
        assert response.status_code == 200
        assert response.data["name"] == "Acme Updated"

    def test_owner_can_patch_description(self, auth_client, workspace):
        response = auth_client.patch(self.url(), {"description": "New description"})
        assert response.status_code == 200
        assert response.data["description"] == "New description"

    def test_owner_can_patch_plan(self, auth_client, workspace):
        response = auth_client.patch(self.url(), {"plan": WorkspacePlan.PRO})
        assert response.status_code == 200
        assert response.data["plan"] == WorkspacePlan.PRO

    def test_non_owner_member_cannot_patch(self, api_client, workspace, other_user):
        WorkspaceService.add_member(workspace, other_user)
        api_client.force_authenticate(user=other_user)
        response = api_client.patch(self.url(), {"name": "Hacked"})
        assert response.status_code == 403

    def test_sa_can_patch_any_workspace(self, api_client, sa_user, workspace):
        api_client.force_authenticate(user=sa_user)
        response = api_client.patch(self.url(), {"name": "SA Updated"})
        assert response.status_code == 200
        assert response.data["name"] == "SA Updated"

    def test_owner_cannot_delete(self, auth_client, workspace):
        response = auth_client.delete(self.url())
        assert response.status_code == 403

    def test_sa_can_delete(self, api_client, sa_user, workspace):
        api_client.force_authenticate(user=sa_user)
        response = api_client.delete(self.url())
        assert response.status_code == 204
        assert not Workspace.objects.filter(slug="acme").exists()

    def test_sa_delete_nonexistent_returns_404(self, api_client, sa_user):
        api_client.force_authenticate(user=sa_user)
        response = api_client.delete(self.url("ghost"))
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# API: WorkspaceMemberListView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkspaceMemberListView:
    def url(self, slug="acme"):
        return f"/api/workspaces/{slug}/members/"

    def test_member_can_list_members(self, auth_client, workspace, user):
        response = auth_client.get(self.url())
        assert response.status_code == 200
        member_ids = [m["user"]["id"] for m in response.data]
        assert str(user.pk) in member_ids

    def test_non_member_gets_404(self, api_client, workspace, other_user):
        api_client.force_authenticate(user=other_user)
        response = api_client.get(self.url())
        assert response.status_code == 404

    def test_owner_can_add_member(self, auth_client, workspace, other_user):
        response = auth_client.post(self.url(), {"user_id": str(other_user.pk)})
        assert response.status_code == 201
        assert WorkspaceMember.objects.filter(workspace=workspace, user=other_user).exists()

    def test_add_member_response_contains_user_info(self, auth_client, workspace, other_user):
        response = auth_client.post(self.url(), {"user_id": str(other_user.pk)})
        assert response.status_code == 201
        assert response.data["user"]["email"] == other_user.email

    def test_add_member_missing_user_id_returns_400(self, auth_client, workspace):
        response = auth_client.post(self.url(), {})
        assert response.status_code == 400

    def test_add_member_unknown_user_id_returns_404(self, auth_client, workspace):
        response = auth_client.post(self.url(), {"user_id": "00000000-0000-0000-0000-000000000000"})
        assert response.status_code == 404

    def test_non_owner_member_cannot_add_member(self, api_client, workspace, other_user, db):
        third = User.objects.create_user(email="charlie@example.com", password="p", display_name="Charlie")
        WorkspaceService.add_member(workspace, other_user)
        api_client.force_authenticate(user=other_user)
        response = api_client.post(self.url(), {"user_id": str(third.pk)})
        assert response.status_code == 403

    def test_add_existing_member_is_idempotent(self, auth_client, workspace, user):
        response = auth_client.post(self.url(), {"user_id": str(user.pk)})
        assert response.status_code == 201
        assert WorkspaceMember.objects.filter(workspace=workspace, user=user).count() == 1


# ---------------------------------------------------------------------------
# API: WorkspaceMemberDetailView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkspaceMemberDetailView:
    def url(self, user_id, slug="acme"):
        return f"/api/workspaces/{slug}/members/{user_id}/"

    def test_owner_can_remove_member(self, auth_client, workspace, other_user):
        WorkspaceService.add_member(workspace, other_user)
        response = auth_client.delete(self.url(other_user.pk))
        assert response.status_code == 204
        assert not WorkspaceMember.objects.filter(workspace=workspace, user=other_user).exists()

    def test_non_owner_cannot_remove_member(self, api_client, workspace, other_user, db):
        third = User.objects.create_user(email="charlie@example.com", password="p", display_name="Charlie")
        WorkspaceService.add_member(workspace, other_user)
        WorkspaceService.add_member(workspace, third)
        api_client.force_authenticate(user=other_user)
        response = api_client.delete(self.url(third.pk))
        assert response.status_code == 403

    def test_sa_can_remove_any_member(self, api_client, sa_user, workspace, other_user):
        WorkspaceService.add_member(workspace, other_user)
        api_client.force_authenticate(user=sa_user)
        response = api_client.delete(self.url(other_user.pk))
        assert response.status_code == 204

    def test_cannot_remove_workspace_owner(self, auth_client, workspace, user):
        response = auth_client.delete(self.url(user.pk))
        assert response.status_code == 400

    def test_remove_nonexistent_user_returns_404(self, auth_client, workspace):
        response = auth_client.delete(self.url("00000000-0000-0000-0000-000000000000"))
        assert response.status_code == 404
