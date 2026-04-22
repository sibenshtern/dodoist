import pytest
from rest_framework.test import APIClient

from projects.models import (
    Board,
    BoardColumn,
    Label,
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
from projects.services import ProjectService, SprintService, WorkspaceService
from projects.invitations import InvitationService
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

    def test_create_workspace_with_plan_ignored(self, user):
        # plan param is accepted for backward-compat but is no longer applied.
        ws = WorkspaceService.create_workspace(owner=user, name="Pro", slug="pro-ws", plan=WorkspacePlan.PRO)
        assert ws.slug == "pro-ws"

    def test_create_workspace_owner_gets_owner_role(self, user):
        from projects.models import WorkspaceMember, WorkspaceRole
        ws = WorkspaceService.create_workspace(owner=user, name="Free", slug="free-ws")
        member = WorkspaceMember.objects.get(workspace=ws, user=user)
        assert member.role == WorkspaceRole.OWNER

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

    def test_create_workspace_with_description(self, auth_client):
        response = auth_client.post(WORKSPACES_URL, {
            "name": "Pro Co", "slug": "pro-co",
            "description": "A pro workspace",
        })
        assert response.status_code == 201
        assert response.data["description"] == "A pro workspace"

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

    def test_owner_can_patch_description(self, auth_client, workspace):
        response = auth_client.patch(self.url(), {"description": "Updated"})
        assert response.status_code == 200
        assert response.data["description"] == "Updated"

    def test_non_owner_member_cannot_patch(self, api_client, workspace, other_user):
        from projects.models import WorkspaceRole
        WorkspaceService.add_member(workspace, other_user, role=WorkspaceRole.MEMBER)
        api_client.force_authenticate(user=other_user)
        response = api_client.patch(self.url(), {"name": "Hacked"})
        assert response.status_code == 403

    def test_sa_can_patch_any_workspace(self, api_client, sa_user, workspace):
        api_client.force_authenticate(user=sa_user)
        response = api_client.patch(self.url(), {"name": "SA Updated"})
        assert response.status_code == 200
        assert response.data["name"] == "SA Updated"

    def test_owner_can_soft_delete(self, auth_client, workspace):
        response = auth_client.delete(self.url())
        assert response.status_code == 200
        assert response.data["deleted_at"] is not None
        workspace.refresh_from_db()
        assert workspace.is_deleted()

    def test_sa_cannot_delete_workspace_they_dont_own(self, api_client, sa_user, workspace):
        api_client.force_authenticate(user=sa_user)
        response = api_client.delete(self.url())
        assert response.status_code == 400

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


# ---------------------------------------------------------------------------
# API: Workspace project list/create
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProjectListCreateView:
    def url(self, slug="acme"):
        return f"/api/workspaces/{slug}/projects/"

    def test_owner_can_list_projects(self, auth_client, workspace, user):
        ProjectService.create_project(workspace=workspace, creator=user, name="Alpha", key="ALP")
        response = auth_client.get(self.url())
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_owner_can_create_project(self, auth_client, workspace):
        response = auth_client.post(
            self.url(),
            {"name": "Beta", "key": "BET", "type": "kanban"},
            format="json",
        )
        assert response.status_code == 201
        assert Project.objects.filter(key="BET").exists()

    def test_non_member_cannot_list_projects(self, api_client, workspace, other_user):
        api_client.force_authenticate(user=other_user)
        response = api_client.get(self.url())
        assert response.status_code in (403, 404)

    def test_unauthenticated_returns_401(self, api_client, workspace):
        response = api_client.get(self.url())
        assert response.status_code == 401

    def test_duplicate_key_returns_400(self, auth_client, workspace, user):
        ProjectService.create_project(workspace=workspace, creator=user, name="Alpha", key="DUP")
        response = auth_client.post(self.url(), {"name": "Other", "key": "DUP", "type": "kanban"}, format="json")
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# API: Project detail
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProjectDetailView:
    @pytest.fixture
    def project(self, workspace, user):
        return ProjectService.create_project(workspace=workspace, creator=user, name="Alpha", key="ALP")

    def test_member_can_get_project(self, auth_client, project):
        response = auth_client.get(f"/api/projects/{project.pk}/")
        assert response.status_code == 200
        assert response.json()["key"] == "ALP"

    def test_non_member_gets_404(self, api_client, project, other_user):
        api_client.force_authenticate(user=other_user)
        response = api_client.get(f"/api/projects/{project.pk}/")
        assert response.status_code in (403, 404)

    def test_owner_can_patch_name(self, auth_client, project):
        response = auth_client.patch(f"/api/projects/{project.pk}/", {"name": "Alpha v2"}, format="json")
        assert response.status_code == 200
        project.refresh_from_db()
        assert project.name == "Alpha v2"

    def test_archive_project(self, auth_client, project):
        response = auth_client.post(f"/api/projects/{project.pk}/archive/")
        assert response.status_code == 200
        project.refresh_from_db()
        assert project.archived_at is not None

    def test_unarchive_project(self, auth_client, project):
        ProjectService.archive_project(project)
        response = auth_client.post(f"/api/projects/{project.pk}/unarchive/")
        assert response.status_code == 200
        project.refresh_from_db()
        assert project.archived_at is None


# ---------------------------------------------------------------------------
# API: Sprints
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSprintViews:
    @pytest.fixture
    def project(self, workspace, user):
        return ProjectService.create_project(workspace=workspace, creator=user, name="Scrum", key="SCR", project_type="scrum")

    @pytest.fixture
    def sprint(self, project, user):
        return SprintService.create_sprint(project=project, creator=user, name="S1")

    def test_list_sprints(self, auth_client, project, sprint):
        resp = auth_client.get(f"/api/projects/{project.pk}/sprints/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_create_sprint(self, auth_client, project):
        resp = auth_client.post(
            f"/api/projects/{project.pk}/sprints/",
            {"name": "New Sprint"},
            format="json",
        )
        assert resp.status_code == 201
        assert Sprint.objects.filter(name="New Sprint").exists()

    def test_get_sprint_detail(self, auth_client, sprint):
        resp = auth_client.get(f"/api/sprints/{sprint.pk}/")
        assert resp.status_code == 200
        assert resp.json()["name"] == "S1"

    def test_start_sprint(self, auth_client, sprint):
        resp = auth_client.post(f"/api/sprints/{sprint.pk}/start/")
        assert resp.status_code == 200
        sprint.refresh_from_db()
        assert sprint.status == SprintStatus.ACTIVE

    def test_cannot_start_already_active_sprint(self, auth_client, sprint):
        SprintService.start_sprint(sprint)
        resp = auth_client.post(f"/api/sprints/{sprint.pk}/start/")
        assert resp.status_code in (400, 409)

    def test_complete_sprint(self, auth_client, project, sprint):
        SprintService.start_sprint(sprint)
        resp = auth_client.post(
            f"/api/sprints/{sprint.pk}/complete/",
            {"incomplete_tasks_action": "backlog"},
            format="json",
        )
        assert resp.status_code == 200
        sprint.refresh_from_db()
        assert sprint.status == SprintStatus.COMPLETED

    def test_non_member_cannot_list_sprints(self, api_client, project, sprint, other_user):
        api_client.force_authenticate(user=other_user)
        resp = api_client.get(f"/api/projects/{project.pk}/sprints/")
        assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# API: Board & columns
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBoardViews:
    @pytest.fixture
    def project(self, workspace, user):
        return ProjectService.create_project(workspace=workspace, creator=user, name="Kanban", key="KAN", project_type="kanban")

    def test_list_boards(self, auth_client, project):
        resp = auth_client.get(f"/api/projects/{project.pk}/boards/")
        assert resp.status_code == 200

    def test_create_board(self, auth_client, project):
        resp = auth_client.post(
            f"/api/projects/{project.pk}/boards/",
            {"name": "Sprint Board", "type": "kanban"},
            format="json",
        )
        assert resp.status_code == 201
        assert Board.objects.filter(name="Sprint Board").exists()

    def test_get_board_detail(self, auth_client, project):
        board = Board.objects.create(project=project, name="B1", type="kanban", is_default=False, created_by=auth_client.handler._force_user if hasattr(auth_client, 'handler') else project.created_by)
        resp = auth_client.get(f"/api/boards/{board.pk}/")
        assert resp.status_code == 200

    def test_list_columns(self, auth_client, project, user):
        board = Board.objects.create(project=project, name="B2", type="kanban", is_default=False, created_by=user)
        resp = auth_client.get(f"/api/boards/{board.pk}/columns/")
        assert resp.status_code == 200

    def test_create_column(self, auth_client, project, user):
        board = Board.objects.create(project=project, name="B3", type="kanban", is_default=False, created_by=user)
        resp = auth_client.post(
            f"/api/boards/{board.pk}/columns/",
            {"name": "Review", "status_mapping": "in_review", "position": 3},
            format="json",
        )
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# API: Labels
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLabelViews:
    def url(self, slug="acme"):
        return f"/api/workspaces/{slug}/labels/"

    def test_list_labels_empty(self, auth_client, workspace):
        resp = auth_client.get(self.url())
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_label(self, auth_client, workspace):
        resp = auth_client.post(self.url(), {"name": "Bug", "color": "#ff0000"}, format="json")
        assert resp.status_code == 201
        assert resp.json()["name"] == "Bug"

    def test_update_label(self, auth_client, workspace, user):
        label = Label.objects.create(workspace=workspace, name="Feature", color="#00ff00", created_by=user)
        resp = auth_client.patch(f"/api/workspaces/acme/labels/{label.pk}/", {"name": "Feature v2"}, format="json")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Feature v2"

    def test_delete_label(self, auth_client, workspace, user):
        label = Label.objects.create(workspace=workspace, name="WontFix", color="#888888", created_by=user)
        resp = auth_client.delete(f"/api/workspaces/acme/labels/{label.pk}/")
        assert resp.status_code == 204
        assert not Label.objects.filter(pk=label.pk).exists()

    def test_non_member_cannot_create_label(self, api_client, workspace, other_user):
        api_client.force_authenticate(user=other_user)
        resp = api_client.post(self.url(), {"name": "Bad", "color": "#fff"}, format="json")
        assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# API: Project members
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProjectMemberViews:
    @pytest.fixture
    def project(self, workspace, user):
        return ProjectService.create_project(workspace=workspace, creator=user, name="Alpha", key="ALX")

    def test_list_members(self, auth_client, project):
        resp = auth_client.get(f"/api/projects/{project.pk}/members/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_add_member(self, auth_client, project, workspace, other_user):
        WorkspaceService.add_member(workspace, other_user)
        resp = auth_client.post(
            f"/api/projects/{project.pk}/members/",
            {"user_id": str(other_user.pk), "role": "DEV"},
            format="json",
        )
        assert resp.status_code == 201
        assert ProjectMember.objects.filter(project=project, user=other_user).exists()

    def test_remove_member(self, auth_client, project, workspace, other_user, user):
        WorkspaceService.add_member(workspace, other_user)
        ProjectService.add_member(project, other_user, ProjectRole.DEV, added_by=user)
        resp = auth_client.delete(f"/api/projects/{project.pk}/members/{other_user.pk}/")
        assert resp.status_code == 204
        assert not ProjectMember.objects.filter(project=project, user=other_user).exists()

    def test_non_member_cannot_list(self, api_client, project, other_user):
        api_client.force_authenticate(user=other_user)
        resp = api_client.get(f"/api/projects/{project.pk}/members/")
        assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# WorkspaceService — roles, transfer, soft-delete, restore, leave
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkspaceRoles:
    @pytest.fixture
    def owner(self, db):
        return UserService.register(email="owner@example.com", password="p", display_name="Owner")

    @pytest.fixture
    def admin_user(self, db):
        return UserService.register(email="admin@example.com", password="p", display_name="Admin")

    @pytest.fixture
    def member_user(self, db):
        return UserService.register(email="member@example.com", password="p", display_name="Member")

    @pytest.fixture
    def team_ws(self, owner):
        return WorkspaceService.create_team_workspace(owner=owner, name="Team", slug="team-roles")

    def test_owner_role_set_on_create(self, team_ws, owner):
        m = WorkspaceMember.objects.get(workspace=team_ws, user=owner)
        assert m.role == WorkspaceRole.OWNER

    def test_add_member_gets_member_role_by_default(self, team_ws, member_user):
        m = WorkspaceService.add_member(team_ws, member_user)
        assert m.role == WorkspaceRole.MEMBER

    def test_change_role_to_admin(self, team_ws, member_user, owner):
        WorkspaceService.add_member(team_ws, member_user)
        m = WorkspaceService.change_role(team_ws, member_user, WorkspaceRole.ADMIN, actor=owner)
        assert m.role == WorkspaceRole.ADMIN

    def test_non_owner_admin_can_change_role(self, team_ws, admin_user, member_user, owner):
        WorkspaceService.add_member(team_ws, admin_user, role=WorkspaceRole.ADMIN)
        WorkspaceService.add_member(team_ws, member_user)
        m = WorkspaceService.change_role(team_ws, member_user, WorkspaceRole.ADMIN, actor=admin_user)
        assert m.role == WorkspaceRole.ADMIN

    def test_member_cannot_change_role(self, team_ws, admin_user, member_user):
        WorkspaceService.add_member(team_ws, admin_user)
        WorkspaceService.add_member(team_ws, member_user)
        with pytest.raises(ValueError, match="Only Owner or Admin"):
            WorkspaceService.change_role(team_ws, admin_user, WorkspaceRole.MEMBER, actor=member_user)

    def test_cannot_change_owner_role(self, team_ws, owner, admin_user):
        WorkspaceService.add_member(team_ws, admin_user, role=WorkspaceRole.ADMIN)
        with pytest.raises(ValueError, match="Cannot change the role of the workspace owner"):
            WorkspaceService.change_role(team_ws, owner, WorkspaceRole.MEMBER, actor=admin_user)

    def test_transfer_ownership(self, team_ws, owner, member_user):
        WorkspaceService.add_member(team_ws, member_user)
        ws = WorkspaceService.transfer_ownership(team_ws, new_owner=member_user, actor=owner)
        assert ws.owner_id == member_user.pk
        old_role = WorkspaceMember.objects.get(workspace=team_ws, user=owner).role
        new_role = WorkspaceMember.objects.get(workspace=team_ws, user=member_user).role
        assert old_role == WorkspaceRole.ADMIN
        assert new_role == WorkspaceRole.OWNER

    def test_transfer_requires_actor_to_be_owner(self, team_ws, member_user, admin_user):
        WorkspaceService.add_member(team_ws, member_user)
        WorkspaceService.add_member(team_ws, admin_user, role=WorkspaceRole.ADMIN)
        with pytest.raises(ValueError, match="Only the current owner"):
            WorkspaceService.transfer_ownership(team_ws, new_owner=member_user, actor=admin_user)

    def test_remove_member_cascades_project_memberships(self, team_ws, owner, member_user):
        WorkspaceService.add_member(team_ws, member_user)
        project = ProjectService.create_project(workspace=team_ws, creator=owner, name="P", key="P")
        ProjectService.add_member(project, member_user, ProjectRole.DEV, added_by=owner)
        assert ProjectMember.objects.filter(project=project, user=member_user).exists()
        WorkspaceService.remove_member(team_ws, member_user)
        assert not ProjectMember.objects.filter(project=project, user=member_user).exists()

    def test_leave_workspace(self, team_ws, member_user):
        WorkspaceService.add_member(team_ws, member_user)
        WorkspaceService.leave(team_ws, member_user)
        assert not WorkspaceMember.objects.filter(workspace=team_ws, user=member_user).exists()

    def test_owner_cannot_leave(self, team_ws, owner):
        with pytest.raises(ValueError, match="transfer ownership"):
            WorkspaceService.leave(team_ws, owner)


@pytest.mark.django_db
class TestWorkspaceSoftDelete:
    @pytest.fixture
    def owner(self, db):
        return UserService.register(email="delowner@example.com", password="p", display_name="DelOwner")

    @pytest.fixture
    def other(self, db):
        return UserService.register(email="other@example.com", password="p", display_name="Other")

    @pytest.fixture
    def team_ws(self, owner):
        return WorkspaceService.create_team_workspace(owner=owner, name="ToDelete", slug="to-delete")

    def test_soft_delete_sets_fields(self, team_ws, owner):
        ws = WorkspaceService.soft_delete(team_ws, actor=owner)
        assert ws.deleted_at is not None
        assert ws.delete_scheduled_for is not None
        assert ws.deleted_by_id == owner.pk

    def test_personal_ws_cannot_be_deleted(self, owner):
        personal = WorkspaceService.create_personal_workspace(owner)
        with pytest.raises(ValueError, match="Personal workspaces"):
            WorkspaceService.soft_delete(personal, actor=owner)

    def test_non_owner_cannot_delete(self, team_ws, other):
        WorkspaceService.add_member(team_ws, other)
        with pytest.raises(ValueError, match="Only the workspace owner"):
            WorkspaceService.soft_delete(team_ws, actor=other)

    def test_restore_clears_fields(self, team_ws, owner):
        WorkspaceService.soft_delete(team_ws, actor=owner)
        team_ws.refresh_from_db()
        ws = WorkspaceService.restore(team_ws, actor=owner)
        assert ws.deleted_at is None
        assert ws.delete_scheduled_for is None
        assert ws.deleted_by is None

    def test_restore_requires_owner(self, team_ws, owner, other):
        WorkspaceService.add_member(team_ws, other)
        WorkspaceService.soft_delete(team_ws, actor=owner)
        team_ws.refresh_from_db()
        with pytest.raises(ValueError, match="Only the workspace owner"):
            WorkspaceService.restore(team_ws, actor=other)

    def test_cannot_delete_already_deleted(self, team_ws, owner):
        WorkspaceService.soft_delete(team_ws, actor=owner)
        team_ws.refresh_from_db()
        with pytest.raises(ValueError, match="already scheduled"):
            WorkspaceService.soft_delete(team_ws, actor=owner)


@pytest.mark.django_db
class TestWorkspaceRoleEndpoints:
    @pytest.fixture
    def owner(self, db):
        return UserService.register(email="ep_owner@example.com", password="p", display_name="EPOwner")

    @pytest.fixture
    def member_user(self, db):
        return UserService.register(email="ep_member@example.com", password="p", display_name="EPMember")

    @pytest.fixture
    def team_ws(self, owner):
        return WorkspaceService.create_team_workspace(owner=owner, name="EP", slug="ep-ws")

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_owner_can_soft_delete(self, team_ws, owner):
        resp = self._client(owner).delete(f"/api/workspaces/{team_ws.slug}/")
        assert resp.status_code == 200
        team_ws.refresh_from_db()
        assert team_ws.deleted_at is not None

    def test_member_cannot_delete(self, team_ws, member_user):
        WorkspaceService.add_member(team_ws, member_user)
        resp = self._client(member_user).delete(f"/api/workspaces/{team_ws.slug}/")
        assert resp.status_code in (400, 403)

    def test_owner_can_restore(self, team_ws, owner):
        WorkspaceService.soft_delete(team_ws, actor=owner)
        team_ws.refresh_from_db()
        resp = self._client(owner).post(f"/api/workspaces/{team_ws.slug}/restore/")
        assert resp.status_code == 200
        team_ws.refresh_from_db()
        assert team_ws.deleted_at is None

    def test_member_can_leave(self, team_ws, member_user):
        WorkspaceService.add_member(team_ws, member_user)
        resp = self._client(member_user).post(f"/api/workspaces/{team_ws.slug}/leave/")
        assert resp.status_code == 204
        assert not WorkspaceMember.objects.filter(workspace=team_ws, user=member_user).exists()

    def test_owner_cannot_leave(self, team_ws, owner):
        resp = self._client(owner).post(f"/api/workspaces/{team_ws.slug}/leave/")
        assert resp.status_code in (400, 403)

    def test_owner_can_transfer(self, team_ws, owner, member_user):
        WorkspaceService.add_member(team_ws, member_user)
        resp = self._client(owner).post(
            f"/api/workspaces/{team_ws.slug}/transfer/",
            {"new_owner_id": str(member_user.pk)},
            format="json",
        )
        assert resp.status_code == 200
        team_ws.refresh_from_db()
        assert team_ws.owner_id == member_user.pk

    def test_admin_can_change_member_role(self, team_ws, owner, member_user):
        admin = UserService.register(email="ep_admin2@example.com", password="p", display_name="Admin2")
        WorkspaceService.add_member(team_ws, admin, role=WorkspaceRole.ADMIN)
        WorkspaceService.add_member(team_ws, member_user)
        resp = self._client(admin).patch(
            f"/api/workspaces/{team_ws.slug}/members/{member_user.pk}/",
            {"role": "ADMIN"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "ADMIN"

    def test_member_cannot_change_roles(self, team_ws, owner, member_user):
        other = UserService.register(email="ep_other2@example.com", password="p", display_name="Other2")
        WorkspaceService.add_member(team_ws, member_user)
        WorkspaceService.add_member(team_ws, other)
        resp = self._client(member_user).patch(
            f"/api/workspaces/{team_ws.slug}/members/{other.pk}/",
            {"role": "ADMIN"},
            format="json",
        )
        assert resp.status_code in (400, 403)


@pytest.mark.django_db
class TestInvitations:
    @pytest.fixture
    def owner(self, db):
        return UserService.register(email="inv_owner@example.com", password="p", display_name="InvOwner")

    @pytest.fixture
    def invitee(self, db):
        return UserService.register(email="invitee@example.com", password="p", display_name="Invitee")

    @pytest.fixture
    def team_ws(self, owner):
        return WorkspaceService.create_team_workspace(owner=owner, name="InvWS", slug="inv-ws")

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_email_invite_creates_invitation(self, team_ws, owner, invitee):
        invite, _ = InvitationService.create_email_invite(
            workspace=team_ws, email=invitee.email, role=WorkspaceRole.MEMBER, invited_by=owner
        )
        assert invite.pk is not None
        assert invite.kind == "email"
        assert invite.token_hash != ""

    def test_accept_email_invite(self, team_ws, owner, invitee):
        _, raw_token = InvitationService.create_email_invite(
            workspace=team_ws, email=invitee.email, role=WorkspaceRole.MEMBER, invited_by=owner
        )
        ws = InvitationService.accept(raw_token, invitee)
        assert ws.pk == team_ws.pk
        assert WorkspaceMember.objects.filter(workspace=team_ws, user=invitee).exists()

    def test_email_mismatch_rejected(self, team_ws, owner):
        other = UserService.register(email="stranger@example.com", password="p", display_name="Stranger")
        _, raw_token = InvitationService.create_email_invite(
            workspace=team_ws, email="specific@example.com", role=WorkspaceRole.MEMBER, invited_by=owner
        )
        with pytest.raises(ValueError, match="INVITE_EMAIL_MISMATCH"):
            InvitationService.accept(raw_token, other)

    def test_expired_invite_rejected(self, team_ws, owner, invitee):
        from django.utils import timezone as tz
        invite, raw_token = InvitationService.create_email_invite(
            workspace=team_ws, email=invitee.email, role=WorkspaceRole.MEMBER, invited_by=owner
        )
        invite.expires_at = tz.now() - tz.timedelta(days=1)
        invite.save()
        with pytest.raises(ValueError, match="INVITE_EXPIRED"):
            InvitationService.accept(raw_token, invitee)

    def test_revoked_invite_rejected(self, team_ws, owner, invitee):
        invite, raw_token = InvitationService.create_email_invite(
            workspace=team_ws, email=invitee.email, role=WorkspaceRole.MEMBER, invited_by=owner
        )
        InvitationService.revoke(invite, actor=owner)
        with pytest.raises(ValueError, match="INVITE_REVOKED"):
            InvitationService.accept(raw_token, invitee)

    def test_invalid_token_rejected(self, team_ws, owner, invitee):
        with pytest.raises(ValueError, match="INVALID_TOKEN"):
            InvitationService.accept("notarealtoken", invitee)

    def test_invite_link_multi_use(self, team_ws, owner):
        user1 = UserService.register(email="u1@example.com", password="p", display_name="U1")
        user2 = UserService.register(email="u2@example.com", password="p", display_name="U2")
        _, raw_token = InvitationService.create_invite_link(
            workspace=team_ws, role=WorkspaceRole.MEMBER, invited_by=owner
        )
        InvitationService.accept(raw_token, user1)
        InvitationService.accept(raw_token, user2)
        invite = WorkspaceInvitation.objects.get(token_hash=__import__("hashlib").sha256(raw_token.encode()).hexdigest())
        assert invite.use_count == 2

    def test_invite_link_max_uses_enforced(self, team_ws, owner):
        user1 = UserService.register(email="mu1@example.com", password="p", display_name="MU1")
        user2 = UserService.register(email="mu2@example.com", password="p", display_name="MU2")
        _, raw_token = InvitationService.create_invite_link(
            workspace=team_ws, role=WorkspaceRole.MEMBER, invited_by=owner, max_uses=1
        )
        InvitationService.accept(raw_token, user1)
        with pytest.raises(ValueError, match="INVITE_EXHAUSTED"):
            InvitationService.accept(raw_token, user2)

    def test_list_pending_excludes_revoked(self, team_ws, owner, invitee):
        invite, _ = InvitationService.create_email_invite(
            workspace=team_ws, email=invitee.email, role=WorkspaceRole.MEMBER, invited_by=owner
        )
        InvitationService.revoke(invite, actor=owner)
        pending = list(InvitationService.list_pending(team_ws))
        assert invite not in pending

    def test_owner_can_create_email_invite_via_api(self, team_ws, owner):
        resp = self._client(owner).post(
            f"/api/workspaces/{team_ws.slug}/invitations/",
            {"email": "new@example.com", "role": "MEMBER"},
            format="json",
        )
        assert resp.status_code == 201

    def test_member_cannot_create_invite_via_api(self, team_ws, owner):
        member = UserService.register(email="inv_m@example.com", password="p", display_name="InvM")
        WorkspaceService.add_member(team_ws, member)
        resp = self._client(member).post(
            f"/api/workspaces/{team_ws.slug}/invitations/",
            {"email": "x@example.com", "role": "MEMBER"},
            format="json",
        )
        assert resp.status_code in (400, 403)

    def test_accept_via_api(self, team_ws, owner, invitee):
        _, raw_token = InvitationService.create_email_invite(
            workspace=team_ws, email=invitee.email, role=WorkspaceRole.MEMBER, invited_by=owner
        )
        resp = self._client(invitee).post(
            "/api/invitations/accept/",
            {"token": raw_token},
            format="json",
        )
        assert resp.status_code == 200
        assert WorkspaceMember.objects.filter(workspace=team_ws, user=invitee).exists()
