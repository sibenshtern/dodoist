import datetime

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from analytics.models import TaskSnapshot, UserMetric
from projects.models import ProjectMember, ProjectRole, SprintStatus
from projects.services import ProjectService, WorkspaceService
from tasks.models import TaskPriority, TaskStatus, TaskType
from tasks.services import TaskService
from users.models import GlobalRole, User
from users.services import UserService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    return UserService.register(email="pm@example.com", password="pass123", display_name="PM User")


@pytest.fixture
def other_user(db):
    return UserService.register(email="dev@example.com", password="pass123", display_name="Dev User")


@pytest.fixture
def workspace(user):
    ws = WorkspaceService.create_workspace(owner=user, name="Acme", slug="acme-analytics")
    from users.services import UserService as _US
    _US.set_active_workspace(user, ws)
    return ws


@pytest.fixture
def scrum_project(workspace, user):
    return ProjectService.create_project(
        workspace=workspace, creator=user, name="Sprint Project", key="SPR", project_type="scrum"
    )


@pytest.fixture
def sprint(scrum_project, user):
    from projects.services import SprintService
    return SprintService.create_sprint(project=scrum_project, creator=user, name="Sprint 1")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def pm_user(db):
    return UserService.register(email="pm2@example.com", password="pass123", display_name="PM2")


@pytest.fixture
def dev_client(db, scrum_project, other_user):
    ProjectMember.objects.create(project=scrum_project, user=other_user, role=ProjectRole.DEV)
    client = APIClient()
    client.force_authenticate(user=other_user)
    return client


# ---------------------------------------------------------------------------
# TaskSnapshot model
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTaskSnapshotModel:
    def test_create_snapshot(self, scrum_project, sprint):
        snap = TaskSnapshot.objects.create(
            project=scrum_project,
            sprint=sprint,
            snapshot_date=datetime.date.today(),
            total_tasks=10,
            completed_tasks=4,
            in_progress_tasks=3,
            total_story_points=20,
            completed_story_points=8,
        )
        assert snap.total_tasks == 10
        assert snap.completed_tasks == 4
        assert str(snap.snapshot_date) == str(datetime.date.today())

    def test_snapshot_without_sprint(self, scrum_project):
        snap = TaskSnapshot.objects.create(
            project=scrum_project,
            snapshot_date=datetime.date.today(),
            total_tasks=5,
        )
        assert snap.sprint is None
        assert snap.total_tasks == 5

    def test_snapshot_str(self, scrum_project, sprint):
        snap = TaskSnapshot.objects.create(
            project=scrum_project,
            sprint=sprint,
            snapshot_date=datetime.date(2026, 1, 15),
        )
        assert "2026-01-15" in str(snap)


# ---------------------------------------------------------------------------
# UserMetric model
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserMetricModel:
    def test_create_user_metric(self, user, scrum_project):
        metric = UserMetric.objects.create(
            user=user,
            project=scrum_project,
            metric_date=datetime.date.today(),
            tasks_created=3,
            tasks_completed=2,
            comments_posted=5,
            logged_minutes=120,
        )
        assert metric.tasks_created == 3
        assert metric.logged_minutes == 120

    def test_user_metric_without_project(self, user):
        metric = UserMetric.objects.create(
            user=user,
            metric_date=datetime.date.today(),
            tasks_completed=1,
        )
        assert metric.project is None


# ---------------------------------------------------------------------------
# GET /api/projects/<pk>/snapshots/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProjectSnapshotListView:
    def test_empty_snapshots(self, auth_client, scrum_project):
        res = auth_client.get(f"/api/projects/{scrum_project.id}/snapshots/")
        assert res.status_code == 200
        assert res.data == []

    def test_returns_project_snapshots(self, auth_client, scrum_project):
        today = datetime.date.today()
        TaskSnapshot.objects.create(
            project=scrum_project, snapshot_date=today, total_tasks=5, completed_tasks=2
        )
        res = auth_client.get(f"/api/projects/{scrum_project.id}/snapshots/")
        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["total_tasks"] == 5

    def test_filter_by_sprint(self, auth_client, scrum_project, sprint):
        today = datetime.date.today()
        TaskSnapshot.objects.create(project=scrum_project, snapshot_date=today, total_tasks=3)
        snap_with_sprint = TaskSnapshot.objects.create(
            project=scrum_project, sprint=sprint, snapshot_date=today, total_tasks=7
        )
        res = auth_client.get(
            f"/api/projects/{scrum_project.id}/snapshots/",
            {"sprint_id": str(sprint.id)},
        )
        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["total_tasks"] == 7

    def test_filter_by_date_range(self, auth_client, scrum_project):
        TaskSnapshot.objects.create(
            project=scrum_project, snapshot_date=datetime.date(2026, 1, 1), total_tasks=1
        )
        TaskSnapshot.objects.create(
            project=scrum_project, snapshot_date=datetime.date(2026, 3, 1), total_tasks=2
        )
        res = auth_client.get(
            f"/api/projects/{scrum_project.id}/snapshots/",
            {"since": "2026-02-01", "until": "2026-04-01"},
        )
        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["total_tasks"] == 2

    def test_non_member_gets_404(self, scrum_project, other_user):
        client = APIClient()
        client.force_authenticate(user=other_user)
        res = client.get(f"/api/projects/{scrum_project.id}/snapshots/")
        assert res.status_code == 404

    def test_unauthenticated_returns_401(self, scrum_project):
        res = APIClient().get(f"/api/projects/{scrum_project.id}/snapshots/")
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/projects/<pk>/metrics/summary/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProjectSummaryView:
    def test_summary_returns_counts(self, auth_client, scrum_project, user):
        TaskService.create_task(project=scrum_project, creator=user, title="Open task")
        done = TaskService.create_task(project=scrum_project, creator=user, title="Done task")
        TaskService.update_status(done, new_status=TaskStatus.DONE, actor=user)

        res = auth_client.get(f"/api/projects/{scrum_project.id}/metrics/summary/")
        assert res.status_code == 200
        data = res.data
        assert data["total_tasks"] >= 2
        assert data["completed_tasks"] >= 1
        assert "velocity" in data

    def test_non_member_gets_404(self, scrum_project, other_user):
        client = APIClient()
        client.force_authenticate(user=other_user)
        res = client.get(f"/api/projects/{scrum_project.id}/metrics/summary/")
        assert res.status_code == 404

    def test_velocity_with_completed_sprints(self, auth_client, scrum_project, user):
        from projects.services import SprintService
        sprint = SprintService.create_sprint(
            project=scrum_project, creator=user, name="S1"
        )
        task = TaskService.create_task(
            project=scrum_project, creator=user, title="Pointed", story_points=5
        )
        task.sprint = sprint
        task.save(update_fields=["sprint"])
        TaskService.update_status(task, new_status=TaskStatus.DONE, actor=user)
        SprintService.start_sprint(sprint)
        SprintService.complete_sprint(sprint)

        res = auth_client.get(f"/api/projects/{scrum_project.id}/metrics/summary/")
        assert res.status_code == 200
        assert res.data["velocity"] >= 5.0


# ---------------------------------------------------------------------------
# GET /api/projects/<pk>/metrics/users/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProjectUserMetricsView:
    def test_pm_can_access(self, auth_client, scrum_project):
        res = auth_client.get(f"/api/projects/{scrum_project.id}/metrics/users/")
        assert res.status_code == 200

    def test_dev_cannot_access(self, dev_client, scrum_project):
        res = dev_client.get(f"/api/projects/{scrum_project.id}/metrics/users/")
        assert res.status_code == 403

    def test_returns_user_metrics(self, auth_client, scrum_project, user):
        today = datetime.date.today()
        UserMetric.objects.create(
            user=user,
            project=scrum_project,
            metric_date=today,
            tasks_completed=3,
            comments_posted=2,
        )
        res = auth_client.get(f"/api/projects/{scrum_project.id}/metrics/users/")
        assert res.status_code == 200
        assert isinstance(res.data, list)


# ---------------------------------------------------------------------------
# GET /api/tasks/search/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTaskSearchView:
    def test_search_finds_by_title(self, auth_client, scrum_project, user):
        TaskService.create_task(project=scrum_project, creator=user, title="OAuth integration bug")
        TaskService.create_task(project=scrum_project, creator=user, title="Unrelated task")

        res = auth_client.get("/api/tasks/search/", {"q": "oauth"})
        assert res.status_code == 200
        assert len(res.data) == 1
        assert "OAuth" in res.data[0]["title"]

    def test_search_case_insensitive(self, auth_client, scrum_project, user):
        TaskService.create_task(project=scrum_project, creator=user, title="Fix the Login flow")
        res = auth_client.get("/api/tasks/search/", {"q": "LOGIN"})
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_short_query_returns_empty(self, auth_client):
        res = auth_client.get("/api/tasks/search/", {"q": "x"})
        assert res.status_code == 200
        assert res.data == []

    def test_missing_query_returns_empty(self, auth_client):
        res = auth_client.get("/api/tasks/search/")
        assert res.status_code == 200
        assert res.data == []

    def test_excludes_deleted_tasks(self, auth_client, scrum_project, user):
        task = TaskService.create_task(
            project=scrum_project, creator=user, title="Deleted search target"
        )
        TaskService.soft_delete(task, actor=user)
        res = auth_client.get("/api/tasks/search/", {"q": "Deleted search"})
        assert res.status_code == 200
        assert len(res.data) == 0

    def test_excludes_tasks_from_non_member_projects(self, scrum_project, user, other_user):
        TaskService.create_task(project=scrum_project, creator=user, title="Secret task omega")
        client = APIClient()
        client.force_authenticate(user=other_user)
        res = client.get("/api/tasks/search/", {"q": "omega"})
        assert res.status_code == 200
        assert len(res.data) == 0

    def test_result_includes_project_metadata(self, auth_client, scrum_project, user):
        TaskService.create_task(project=scrum_project, creator=user, title="Metadata check")
        res = auth_client.get("/api/tasks/search/", {"q": "Metadata"})
        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["project_name"] == scrum_project.name
        assert "project_color" in res.data[0]

    def test_unauthenticated_returns_401(self):
        res = APIClient().get("/api/tasks/search/", {"q": "test"})
        assert res.status_code == 401

    def test_elevated_user_sees_all_projects(self, scrum_project, user):
        sa = User.objects.create_user(
            email="sa@example.com", password="p", display_name="SA"
        )
        sa.global_role = GlobalRole.SA
        sa.save()
        TaskService.create_task(project=scrum_project, creator=user, title="SA visible task zeta")
        sa_client = APIClient()
        sa_client.force_authenticate(user=sa)
        res = sa_client.get("/api/tasks/search/", {"q": "zeta"})
        assert res.status_code == 200
        assert len(res.data) >= 1
