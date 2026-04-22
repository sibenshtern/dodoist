# Home Page Live Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all mock data on the `/home` dashboard page with live data fetched from the backend via 7 API calls.

**Architecture:** Add 5 new backend endpoints (users/me, dashboard/stats, tasks/today, activity, sprints/progress) and modify the projects endpoint to include task counts. On the frontend, replace `DashboardService` mock `of()` calls with real HTTP calls, add a `UserService`, and update `HomeComponent` to sequence dependent calls (workspace → projects → sprint).

**Tech Stack:** Django 4.2, Django REST Framework 3.15, Angular 21, Angular Signals, HttpClient

---

## File Map

### Backend — create/modify

| File | Action | Responsibility |
|------|--------|----------------|
| `users/views.py` | Modify | Add `MeView` |
| `users/urls.py` | Modify | Add `/api/users/me` |
| `users/tests.py` | Modify | Add `TestMeView` |
| `tasks/views.py` | Modify | Add `DashboardStatsView`, `TodayTasksView`, `ActivityView` |
| `tasks/urls.py` | Modify | Add 3 new URL patterns |
| `tasks/tests.py` | Modify | Add view tests for the 3 new endpoints |
| `projects/views.py` | Modify | Add `SprintProgressView`; add `open_tasks` + `progress` to `ProjectSerializer` |
| `projects/urls.py` | Modify | Add `/api/sprints/<uuid>/progress/` |
| `projects/tests.py` | Modify | Add tests for sprint progress endpoint + project serializer fields |

### Frontend — create/modify

| File | Action | Responsibility |
|------|--------|----------------|
| `src/app/services/user.service.ts` | Create | `getCurrentUser()` → `GET /api/users/me` |
| `src/app/services/dashboard.service.ts` | Modify | Replace all `of(...)` mocks with real HTTP; update `ProjectSummary` interface |
| `src/app/pages/home/home.component.ts` | Modify | Inject `UserService`; remove hardcoded name/workspace; sequence API calls |

---

## Task 1: GET /api/users/me

**Files:**
- Modify: `dodoist-backend/users/views.py`
- Modify: `dodoist-backend/users/urls.py`
- Modify: `dodoist-backend/users/tests.py`

- [ ] **Step 1: Write failing test**

Add to `users/tests.py` (after existing test classes):

```python
from rest_framework.test import APIClient
import hashlib, secrets
from datetime import timedelta


@pytest.mark.django_db
class TestMeView:
    def _auth_client(self, user):
        raw = secrets.token_hex(32)
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        UserService.create_session(
            user=user,
            token_hash=token_hash,
            expires_at=timezone.now() + timedelta(days=1),
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
        return client

    def test_me_returns_current_user(self, user):
        client = self._auth_client(user)
        response = client.get("/api/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "alice@example.com"
        assert data["display_name"] == "Alice"
        assert "id" in data
        assert "avatar_url" in data
        assert "timezone" in data

    def test_me_requires_auth(self):
        client = APIClient()
        response = client.get("/api/users/me")
        assert response.status_code == 403
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd dodoist-backend && source venv/bin/activate
pytest users/tests.py::TestMeView -v
```
Expected: `FAILED` — `404` or `ImportError`

- [ ] **Step 3: Implement MeView**

In `users/views.py`, add after the existing imports and `SESSION_DURATION_DAYS`:

```python
class MeView(APIView):
    """
    GET /api/users/me

    Returns the authenticated user's profile.
    """

    def get(self, request):
        user = request.user
        return Response({
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "timezone": user.timezone,
        })
```

- [ ] **Step 4: Register URL**

In `users/urls.py`, add to `urlpatterns`:

```python
from .views import LoginView, LogoutView, MeView, RegisterView

urlpatterns = [
    path("api/auth/register", RegisterView.as_view(), name="auth-register"),
    path("api/auth/login", LoginView.as_view(), name="auth-login"),
    path("api/auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("api/users/me", MeView.as_view(), name="users-me"),
]
```

- [ ] **Step 5: Run test — expect PASS**

```bash
pytest users/tests.py::TestMeView -v
```
Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add users/views.py users/urls.py users/tests.py
git commit -m "feat: add GET /api/users/me endpoint"
```

---

## Task 2: GET /api/dashboard/stats/

**Files:**
- Modify: `dodoist-backend/tasks/views.py`
- Modify: `dodoist-backend/tasks/urls.py`
- Modify: `dodoist-backend/tasks/tests.py`

The endpoint returns task statistics for the authenticated user:
- `open_tasks` — tasks assigned to user, status not in (done, cancelled), not deleted
- `open_tasks_delta` — tasks assigned to user created in last 24 h that are open
- `done_this_week` — tasks assigned to user with `completed_at` ≥ Monday 00:00 UTC this week
- `done_this_week_delta_pct` — `(done_this_week / done_last_week - 1) * 100`, rounded, or 0 if no last-week data
- `story_points` — sum of `story_points` for done tasks in the most recent active sprint in the user's projects
- `story_points_total` — sum of `story_points` for all tasks in that same sprint
- `overdue` — tasks assigned to user where `due_date < now()` and status not in (done, cancelled), not deleted

- [ ] **Step 1: Write failing test**

Add to `tasks/tests.py` (after existing test classes):

```python
import hashlib, secrets
from datetime import timedelta


def _make_auth_client(user):
    raw = secrets.token_hex(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    UserService.create_session(
        user=user,
        token_hash=token_hash,
        expires_at=timezone.now() + timedelta(days=1),
    )
    from rest_framework.test import APIClient
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    return client


@pytest.mark.django_db
class TestDashboardStatsView:
    def test_returns_stats_shape(self, user, project):
        client = _make_auth_client(user)
        response = client.get("/api/dashboard/stats/")
        assert response.status_code == 200
        data = response.json()
        for key in ("open_tasks", "open_tasks_delta", "done_this_week",
                    "done_this_week_delta_pct", "story_points",
                    "story_points_total", "overdue"):
            assert key in data, f"missing key: {key}"

    def test_open_tasks_counts_assigned(self, user, project):
        TaskService.create_task(project=project, creator=user, title="T1", assigned_to=user)
        TaskService.create_task(project=project, creator=user, title="T2", assigned_to=user)
        client = _make_auth_client(user)
        response = client.get("/api/dashboard/stats/")
        assert response.json()["open_tasks"] == 2

    def test_overdue_counts_past_due(self, user, project):
        t = TaskService.create_task(project=project, creator=user, title="Late", assigned_to=user)
        t.due_date = timezone.now() - timedelta(days=2)
        t.save()
        client = _make_auth_client(user)
        data = client.get("/api/dashboard/stats/").json()
        assert data["overdue"] >= 1
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tasks/tests.py::TestDashboardStatsView -v
```
Expected: FAIL — 404

- [ ] **Step 3: Implement DashboardStatsView**

Add the following helper and view to `tasks/views.py` (after existing imports):

```python
from datetime import timedelta

from django.db.models import Q, Sum
from django.utils import timezone as tz

from projects.models import Project, ProjectMember, Sprint, SprintStatus, TaskStatus


def _get_monday_of_week(dt):
    """Returns midnight UTC on Monday of the week containing dt."""
    days_since_monday = dt.weekday()
    monday = (dt - timedelta(days=days_since_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return monday


class DashboardStatsView(APIView):
    """
    GET /api/dashboard/stats/

    Returns aggregated task statistics for the authenticated user.
    """

    def get(self, request):
        user = request.user
        now = tz.now()

        open_statuses = [
            TaskStatus.BACKLOG,
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
            TaskStatus.IN_REVIEW,
        ]

        base_qs = Task.objects.filter(
            assigned_to=user,
            deleted_at__isnull=True,
        )

        open_tasks = base_qs.filter(status__in=open_statuses).count()

        yesterday = now - timedelta(days=1)
        open_tasks_delta = base_qs.filter(
            status__in=open_statuses,
            created_at__gte=yesterday,
        ).count()

        monday_this_week = _get_monday_of_week(now)
        monday_last_week = monday_this_week - timedelta(weeks=1)

        done_this_week = base_qs.filter(
            status=TaskStatus.DONE,
            completed_at__gte=monday_this_week,
        ).count()

        done_last_week = base_qs.filter(
            status=TaskStatus.DONE,
            completed_at__gte=monday_last_week,
            completed_at__lt=monday_this_week,
        ).count()

        if done_last_week > 0:
            done_this_week_delta_pct = round((done_this_week / done_last_week - 1) * 100)
        else:
            done_this_week_delta_pct = 0

        overdue = base_qs.filter(
            status__in=open_statuses,
            due_date__lt=now,
        ).count()

        # Story points from the most recent active sprint in any project the user is a member of
        user_project_ids = ProjectMember.objects.filter(user=user).values_list("project_id", flat=True)
        active_sprint = (
            Sprint.objects.filter(
                project_id__in=user_project_ids,
                status=SprintStatus.ACTIVE,
            )
            .order_by("-start_date")
            .first()
        )

        story_points = 0
        story_points_total = 0
        if active_sprint:
            sprint_tasks = Task.objects.filter(
                sprint=active_sprint,
                deleted_at__isnull=True,
            )
            story_points = sprint_tasks.filter(status=TaskStatus.DONE).aggregate(
                total=Sum("story_points")
            )["total"] or 0
            story_points_total = sprint_tasks.aggregate(
                total=Sum("story_points")
            )["total"] or 0

        return Response({
            "open_tasks": open_tasks,
            "open_tasks_delta": open_tasks_delta,
            "done_this_week": done_this_week,
            "done_this_week_delta_pct": done_this_week_delta_pct,
            "story_points": story_points,
            "story_points_total": story_points_total,
            "overdue": overdue,
        })
```

- [ ] **Step 4: Register URL**

In `tasks/urls.py`, add:

```python
from .views import (
    ...existing imports...,
    DashboardStatsView,
)

urlpatterns = [
    ...existing patterns...,
    path("api/dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
]
```

- [ ] **Step 5: Run test — expect PASS**

```bash
pytest tasks/tests.py::TestDashboardStatsView -v
```
Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add tasks/views.py tasks/urls.py tasks/tests.py
git commit -m "feat: add GET /api/dashboard/stats/ endpoint"
```

---

## Task 3: GET /api/tasks/today/

**Files:**
- Modify: `dodoist-backend/tasks/views.py`
- Modify: `dodoist-backend/tasks/urls.py`
- Modify: `dodoist-backend/tasks/tests.py`

Returns tasks assigned to the current user due within ±3 days of today (plus any overdue), with label info and a human-readable `due_label`. Tasks with `status=done` have `done=true`.

- [ ] **Step 1: Write failing test**

Add to `tasks/tests.py`:

```python
@pytest.mark.django_db
class TestTodayTasksView:
    def test_returns_tasks_assigned_to_user(self, user, project):
        t = TaskService.create_task(
            project=project, creator=user, title="My Task", assigned_to=user
        )
        t.due_date = timezone.now()
        t.save()

        client = _make_auth_client(user)
        response = client.get("/api/tasks/today/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "My Task"
        assert data[0]["due_label"] == "Today"
        assert data[0]["done"] is False
        assert "label_name" in data[0]
        assert "label_color" in data[0]

    def test_excludes_tasks_not_assigned_to_user(self, user, other_user, project):
        t = TaskService.create_task(
            project=project, creator=user, title="Not Mine", assigned_to=other_user
        )
        t.due_date = timezone.now()
        t.save()
        client = _make_auth_client(user)
        response = client.get("/api/tasks/today/")
        assert response.json() == []

    def test_done_task_has_done_true(self, user, project):
        t = TaskService.create_task(
            project=project, creator=user, title="Done", assigned_to=user
        )
        t.due_date = timezone.now()
        t.status = TaskStatus.DONE
        t.completed_at = timezone.now()
        t.save()
        client = _make_auth_client(user)
        data = client.get("/api/tasks/today/").json()
        assert len(data) == 1
        assert data[0]["done"] is True
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tasks/tests.py::TestTodayTasksView -v
```
Expected: FAIL — 404

- [ ] **Step 3: Implement TodayTasksView**

Add helper `_due_label` and `TodayTasksView` to `tasks/views.py`:

```python
def _due_label(due_date, now) -> str:
    """Returns a human-readable label relative to today."""
    today = now.date()
    due = due_date.date()
    delta = (due - today).days
    if delta <= -2:
        return f"{due.day} {due.strftime('%b')}"
    if delta == -1:
        return "Yesterday"
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Tomorrow"
    return f"{due.day} {due.strftime('%b')}"


class TodayTasksView(APIView):
    """
    GET /api/tasks/today/

    Returns tasks assigned to the authenticated user due within ±3 days of today,
    including overdue tasks. Cancelled and deleted tasks are excluded.
    """

    def get(self, request):
        now = tz.now()
        window_start = now - timedelta(days=2)
        window_end = now + timedelta(days=3)

        tasks = (
            Task.objects.filter(
                assigned_to=request.user,
                deleted_at__isnull=True,
                due_date__range=(window_start, window_end),
            )
            .exclude(status=TaskStatus.CANCELLED)
            .select_related("assigned_to")
            .prefetch_related("task_labels__label")
            .order_by("due_date")
        )

        result = []
        for task in tasks:
            first_label = task.task_labels.first()
            label_name = first_label.label.name if first_label else ""
            label_color = first_label.label.color if first_label else ""

            result.append({
                "id": str(task.id),
                "title": task.title,
                "label_name": label_name,
                "label_color": label_color,
                "due_label": _due_label(task.due_date, now),
                "done": task.status == TaskStatus.DONE,
            })

        return Response(result)
```

- [ ] **Step 4: Register URL**

In `tasks/urls.py`, add to imports and patterns:

```python
from .views import (
    ...existing...,
    DashboardStatsView,
    TodayTasksView,
)

urlpatterns = [
    ...existing...,
    path("api/dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("api/tasks/today/", TodayTasksView.as_view(), name="tasks-today"),
]
```

- [ ] **Step 5: Run test — expect PASS**

```bash
pytest tasks/tests.py::TestTodayTasksView -v
```
Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add tasks/views.py tasks/urls.py tasks/tests.py
git commit -m "feat: add GET /api/tasks/today/ endpoint"
```

---

## Task 4: GET /api/activity/

**Files:**
- Modify: `dodoist-backend/tasks/views.py`
- Modify: `dodoist-backend/tasks/urls.py`
- Modify: `dodoist-backend/tasks/tests.py`

Returns the last N activity log entries for projects the authenticated user is a member of. Each entry resolves the target entity name (task title, project name, or sprint name).

- [ ] **Step 1: Write failing test**

Add to `tasks/tests.py`:

```python
@pytest.mark.django_db
class TestActivityView:
    def test_returns_activity_items(self, user, project, task):
        ActivityLog.objects.create(
            entity_type="task",
            entity_id=task.id,
            actor=user,
            action="completed",
            project=project,
            new_value={"title": task.title},
        )
        client = _make_auth_client(user)
        response = client.get("/api/activity/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["actor_name"] == "Alice"
        assert data[0]["action"] == "completed"
        assert data[0]["target"] == task.title
        assert "time_ago" in data[0]

    def test_excludes_activity_from_other_projects(self, user, other_user, project):
        from projects.services import ProjectService, WorkspaceService
        other_workspace = WorkspaceService.create_workspace(
            owner=other_user, name="Other", slug="other"
        )
        other_project = ProjectService.create_project(
            workspace=other_workspace, creator=other_user, name="Other", key="OTH"
        )
        ActivityLog.objects.create(
            entity_type="project",
            entity_id=other_project.id,
            actor=other_user,
            action="created",
            project=other_project,
        )
        client = _make_auth_client(user)
        response = client.get("/api/activity/")
        assert response.json() == []

    def test_limit_param(self, user, project, task):
        for i in range(15):
            ActivityLog.objects.create(
                entity_type="task",
                entity_id=task.id,
                actor=user,
                action=f"action_{i}",
                project=project,
            )
        client = _make_auth_client(user)
        assert len(client.get("/api/activity/?limit=5").json()) == 5
        assert len(client.get("/api/activity/").json()) == 10  # default
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tasks/tests.py::TestActivityView -v
```
Expected: FAIL — 404

- [ ] **Step 3: Implement ActivityView**

Add helper `_time_ago` and `ActivityView` to `tasks/views.py`:

```python
def _time_ago(dt, now) -> str:
    """Returns a human-readable time delta string."""
    diff = now - dt
    total_seconds = int(diff.total_seconds())
    if total_seconds < 60:
        return "just now"
    if total_seconds < 3600:
        return f"{total_seconds // 60}m ago"
    if total_seconds < 86400:
        return f"{total_seconds // 3600}h ago"
    return f"{diff.days}d ago"


def _resolve_target(log) -> str:
    """
    Returns a human-readable name for the activity's target entity.
    Falls back to new_value['title'] if stored, then entity_id.
    """
    if log.new_value and isinstance(log.new_value, dict) and "title" in log.new_value:
        return log.new_value["title"]
    if log.entity_type == "task":
        try:
            return Task.objects.get(pk=log.entity_id).title
        except Task.DoesNotExist:
            pass
    if log.entity_type == "project":
        from projects.models import Project as _Project
        try:
            return _Project.objects.get(pk=log.entity_id).name
        except _Project.DoesNotExist:
            pass
    if log.entity_type == "sprint":
        from projects.models import Sprint as _Sprint
        try:
            return _Sprint.objects.get(pk=log.entity_id).name
        except _Sprint.DoesNotExist:
            pass
    return str(log.entity_id)


class ActivityView(APIView):
    """
    GET /api/activity/?limit=<n>

    Returns the most recent activity entries for projects the authenticated
    user is a member of. Default limit is 10, maximum is 50.
    """

    def get(self, request):
        limit = min(int(request.query_params.get("limit", 10)), 50)
        now = tz.now()

        user_project_ids = ProjectMember.objects.filter(
            user=request.user
        ).values_list("project_id", flat=True)

        logs = (
            ActivityLog.objects.filter(project_id__in=user_project_ids)
            .select_related("actor")
            .order_by("-created_at")[:limit]
        )

        return Response([
            {
                "id": str(log.id),
                "actor_name": log.actor.display_name,
                "action": log.action,
                "target": _resolve_target(log),
                "time_ago": _time_ago(log.created_at, now),
            }
            for log in logs
        ])
```

- [ ] **Step 4: Register URL**

In `tasks/urls.py`:

```python
from .views import (
    ...existing...,
    ActivityView,
    DashboardStatsView,
    TodayTasksView,
)

urlpatterns = [
    ...existing...,
    path("api/dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("api/tasks/today/", TodayTasksView.as_view(), name="tasks-today"),
    path("api/activity/", ActivityView.as_view(), name="activity"),
]
```

- [ ] **Step 5: Run test — expect PASS**

```bash
pytest tasks/tests.py::TestActivityView -v
```
Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add tasks/views.py tasks/urls.py tasks/tests.py
git commit -m "feat: add GET /api/activity/ endpoint"
```

---

## Task 5: Sprint progress endpoint + project task counts

**Files:**
- Modify: `dodoist-backend/projects/views.py`
- Modify: `dodoist-backend/projects/serializers.py`
- Modify: `dodoist-backend/projects/urls.py`
- Modify: `dodoist-backend/projects/tests.py`

Adds `open_tasks` and `progress` to `ProjectSerializer`, and a new `SprintProgressView` at `GET /api/sprints/<uuid>/progress/`.

- [ ] **Step 1: Write failing tests**

Add to `projects/tests.py`:

```python
import hashlib, secrets
from datetime import timedelta


def _make_auth_client(user):
    from rest_framework.test import APIClient
    raw = secrets.token_hex(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    UserService.create_session(
        user=user,
        token_hash=token_hash,
        expires_at=timezone.now() + timedelta(days=1),
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    return client


@pytest.fixture
def sprint(project, user):
    from projects.models import Sprint, SprintStatus
    return Sprint.objects.create(
        project=project,
        name="Sprint 1",
        status=SprintStatus.ACTIVE,
        start_date=timezone.now().date(),
        end_date=(timezone.now() + timedelta(days=7)).date(),
        created_by=user,
    )


@pytest.mark.django_db
class TestProjectSerializerTaskCounts:
    def test_project_list_includes_open_tasks_and_progress(self, user, workspace, project):
        from tasks.services import TaskService
        from projects.models import TaskStatus
        t1 = TaskService.create_task(project=project, creator=user, title="Open 1")
        t2 = TaskService.create_task(project=project, creator=user, title="Open 2")
        t3 = TaskService.create_task(project=project, creator=user, title="Done 1")
        t3.status = TaskStatus.DONE
        t3.save()

        client = _make_auth_client(user)
        response = client.get(f"/api/workspaces/{workspace.slug}/projects/")
        assert response.status_code == 200
        proj = response.json()[0]
        assert proj["open_tasks"] == 2
        assert proj["progress"] == 33  # 1 done out of 3 total


@pytest.mark.django_db
class TestSprintProgressView:
    def test_returns_sprint_progress(self, user, project, sprint):
        from tasks.services import TaskService
        from projects.models import TaskStatus
        t1 = TaskService.create_task(project=project, creator=user, title="D", sprint=sprint)
        t1.status = TaskStatus.DONE
        t1.story_points = 5
        t1.save()
        t2 = TaskService.create_task(project=project, creator=user, title="IP", sprint=sprint)
        t2.status = TaskStatus.IN_PROGRESS
        t2.story_points = 3
        t2.save()

        client = _make_auth_client(user)
        response = client.get(f"/api/sprints/{sprint.id}/progress/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Sprint 1"
        assert data["done"] == 1
        assert data["in_progress"] == 1
        assert data["story_points_done"] == 5
        assert data["story_points_total"] == 8
        assert "days_left" in data
        assert "blocked" in data

    def test_sprint_requires_membership(self, other_user, project, sprint):
        client = _make_auth_client(other_user)
        response = client.get(f"/api/sprints/{sprint.id}/progress/")
        assert response.status_code == 403
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest projects/tests.py::TestProjectSerializerTaskCounts projects/tests.py::TestSprintProgressView -v
```
Expected: FAIL

- [ ] **Step 3: Add open_tasks + progress to ProjectSerializer**

In `projects/serializers.py`, add to `ProjectSerializer`:

```python
from projects.models import TaskStatus  # add to existing import

class ProjectSerializer(serializers.ModelSerializer):
    created_by = UserBriefSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    active_sprint = serializers.SerializerMethodField()
    current_user_role = serializers.SerializerMethodField()
    open_tasks = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id", "workspace", "name", "description", "key", "color",
            "icon_url", "status", "type", "is_private", "created_by",
            "created_at", "updated_at", "archived_at",
            "member_count", "active_sprint", "current_user_role",
            "open_tasks", "progress",
        ]

    # ... existing methods unchanged ...

    def get_open_tasks(self, obj: Project) -> int:
        return obj.tasks.filter(
            deleted_at__isnull=True,
            status__in=[
                TaskStatus.BACKLOG, TaskStatus.TODO,
                TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW,
            ],
        ).count()

    def get_progress(self, obj: Project) -> int:
        tasks = obj.tasks.filter(
            deleted_at__isnull=True,
        ).exclude(status=TaskStatus.CANCELLED)
        total = tasks.count()
        if total == 0:
            return 0
        done = tasks.filter(status=TaskStatus.DONE).count()
        return round(done / total * 100)
```

- [ ] **Step 4: Implement SprintProgressView**

In `projects/views.py`, add:

```python
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.utils import timezone as tz

from .models import Project, ProjectMember, Sprint, SprintStatus, TaskStatus


class SprintProgressView(APIView):
    """
    GET /api/sprints/<uuid:pk>/progress/

    Returns computed progress metrics for a sprint.
    Requires the authenticated user to be a member of the sprint's project.
    """

    def get(self, request, pk):
        sprint = get_object_or_404(Sprint, pk=pk)

        if not request.user.has_elevated_access():
            is_member = ProjectMember.objects.filter(
                project=sprint.project, user=request.user
            ).exists()
            if not is_member:
                return Response({"detail": "You are not a member of this project."}, status=403)

        tasks = sprint.tasks.filter(deleted_at__isnull=True)

        done_count = tasks.filter(status=TaskStatus.DONE).count()
        in_progress_count = tasks.filter(
            status__in=[TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW]
        ).count()
        blocked_count = tasks.filter(
            dependencies__type="is_blocked_by"
        ).distinct().count()

        sp_done = tasks.filter(status=TaskStatus.DONE).aggregate(
            total=Sum("story_points")
        )["total"] or 0
        sp_total = tasks.aggregate(total=Sum("story_points"))["total"] or 0

        today = tz.now().date()
        if sprint.end_date:
            days_left = max(0, (sprint.end_date - today).days)
        else:
            days_left = 0

        return Response({
            "name": sprint.name,
            "story_points_done": sp_done,
            "story_points_total": sp_total,
            "done": done_count,
            "in_progress": in_progress_count,
            "blocked": blocked_count,
            "days_left": days_left,
        })
```

- [ ] **Step 5: Register URL**

In `projects/urls.py`, add:

```python
from .views import (
    ...existing imports...,
    SprintProgressView,
)

urlpatterns = [
    ...existing...,
    path("api/sprints/<uuid:pk>/progress/", SprintProgressView.as_view(), name="sprint-progress"),
]
```

- [ ] **Step 6: Run tests — expect PASS**

```bash
pytest projects/tests.py::TestProjectSerializerTaskCounts projects/tests.py::TestSprintProgressView -v
```
Expected: all PASS

- [ ] **Step 7: Run full backend suite**

```bash
pytest users/tests.py projects/tests.py tasks/tests.py -q
```
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add projects/views.py projects/serializers.py projects/urls.py projects/tests.py
git commit -m "feat: add sprint progress endpoint and task counts to project serializer"
```

---

## Task 6: Angular UserService

**Files:**
- Create: `dodoist-app/src/app/services/user.service.ts`

- [ ] **Step 1: Create UserService**

```typescript
// src/app/services/user.service.ts
import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

const API_BASE = 'http://localhost:8000';

export interface CurrentUser {
  id: string;
  email: string;
  display_name: string;
  avatar_url: string;
  timezone: string;
}

@Injectable({ providedIn: 'root' })
export class UserService {
  private readonly http = inject(HttpClient);

  getCurrentUser(): Observable<CurrentUser> {
    return this.http.get<CurrentUser>(`${API_BASE}/api/users/me`);
  }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd dodoist-app && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add src/app/services/user.service.ts
git commit -m "feat: add UserService with getCurrentUser()"
```

---

## Task 7: Replace DashboardService mocks with HTTP calls

**Files:**
- Modify: `dodoist-app/src/app/services/dashboard.service.ts`

Replace all `of(...)` mocks. Add `getWorkspaces()`. Update `ProjectSummary` to include `activeSprintId`. Change `getProjects` to accept a workspace slug. Change `getActiveSprint` to accept a sprint ID.

- [ ] **Step 1: Rewrite DashboardService**

Replace the full file content of `dashboard.service.ts`:

```typescript
import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

const API_BASE = 'http://localhost:8000';

export interface DashboardStats {
  openTasks: number;
  openTasksDelta: number;
  doneThisWeek: number;
  doneThisWeekDeltaPct: number;
  storyPoints: number;
  storyPointsTotal: number;
  overdue: number;
}

export interface TodayTask {
  id: string;
  title: string;
  label: string;
  labelColor: string;
  labelBg: string;
  dueLabel: string;
  done: boolean;
}

export interface ProjectSummary {
  id: string;
  name: string;
  color: string;
  progress: number;
  openTasks: number;
  activeSprintId: string | null;
}

export interface ActivityItem {
  id: string;
  actorName: string;
  action: string;
  target: string;
  timeAgo: string;
}

export interface SprintProgress {
  name: string;
  storyPointsDone: number;
  storyPointsTotal: number;
  done: number;
  inProgress: number;
  blocked: number;
  daysLeft: number;
}

export interface Workspace {
  id: string;
  slug: string;
  name: string;
  plan: string;
}

/** Converts a hex color to a very light background (10% opacity on white). */
function lightBackground(hex: string): string {
  if (!hex || hex.length < 7) return '#f5f5f5';
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const lr = Math.round(r * 0.12 + 255 * 0.88);
  const lg = Math.round(g * 0.12 + 255 * 0.88);
  const lb = Math.round(b * 0.12 + 255 * 0.88);
  return `rgb(${lr}, ${lg}, ${lb})`;
}

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private readonly http = inject(HttpClient);

  getWorkspaces(): Observable<Workspace[]> {
    return this.http.get<Workspace[]>(`${API_BASE}/api/workspaces/`);
  }

  getStats(): Observable<DashboardStats> {
    return this.http
      .get<{
        open_tasks: number;
        open_tasks_delta: number;
        done_this_week: number;
        done_this_week_delta_pct: number;
        story_points: number;
        story_points_total: number;
        overdue: number;
      }>(`${API_BASE}/api/dashboard/stats/`)
      .pipe(
        map(r => ({
          openTasks: r.open_tasks,
          openTasksDelta: r.open_tasks_delta,
          doneThisWeek: r.done_this_week,
          doneThisWeekDeltaPct: r.done_this_week_delta_pct,
          storyPoints: r.story_points,
          storyPointsTotal: r.story_points_total,
          overdue: r.overdue,
        }))
      );
  }

  getTodayTasks(): Observable<TodayTask[]> {
    return this.http
      .get<
        {
          id: string;
          title: string;
          label_name: string;
          label_color: string;
          due_label: string;
          done: boolean;
        }[]
      >(`${API_BASE}/api/tasks/today/`)
      .pipe(
        map(items =>
          items.map(item => ({
            id: item.id,
            title: item.title,
            label: item.label_name,
            labelColor: item.label_color || '#8a8680',
            labelBg: lightBackground(item.label_color),
            dueLabel: item.due_label,
            done: item.done,
          }))
        )
      );
  }

  getProjects(workspaceSlug: string): Observable<ProjectSummary[]> {
    return this.http
      .get<
        {
          id: string;
          name: string;
          color: string;
          progress: number;
          open_tasks: number;
          active_sprint: { id: string } | null;
        }[]
      >(`${API_BASE}/api/workspaces/${workspaceSlug}/projects/`)
      .pipe(
        map(items =>
          items.map(item => ({
            id: item.id,
            name: item.name,
            color: item.color || '#8a8680',
            progress: item.progress,
            openTasks: item.open_tasks,
            activeSprintId: item.active_sprint?.id ?? null,
          }))
        )
      );
  }

  getActivity(limit = 10): Observable<ActivityItem[]> {
    return this.http
      .get<
        {
          id: string;
          actor_name: string;
          action: string;
          target: string;
          time_ago: string;
        }[]
      >(`${API_BASE}/api/activity/?limit=${limit}`)
      .pipe(
        map(items =>
          items.map(item => ({
            id: item.id,
            actorName: item.actor_name,
            action: item.action,
            target: item.target,
            timeAgo: item.time_ago,
          }))
        )
      );
  }

  getActiveSprint(sprintId: string): Observable<SprintProgress> {
    return this.http
      .get<{
        name: string;
        story_points_done: number;
        story_points_total: number;
        done: number;
        in_progress: number;
        blocked: number;
        days_left: number;
      }>(`${API_BASE}/api/sprints/${sprintId}/progress/`)
      .pipe(
        map(r => ({
          name: r.name,
          storyPointsDone: r.story_points_done,
          storyPointsTotal: r.story_points_total,
          done: r.done,
          inProgress: r.in_progress,
          blocked: r.blocked,
          daysLeft: r.days_left,
        }))
      );
  }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd dodoist-app && npx tsc --noEmit
```
Expected: no errors (there will be errors until HomeComponent is updated in the next task — that's OK, fix them now by noting the compile error and continuing to Task 8)

- [ ] **Step 3: Commit**

```bash
git add src/app/services/dashboard.service.ts
git commit -m "feat: replace DashboardService mocks with real HTTP calls"
```

---

## Task 8: Update HomeComponent

**Files:**
- Modify: `dodoist-app/src/app/pages/home/home.component.ts`

Remove hardcoded user/workspace signals. Inject `UserService`. Sequence workspace → projects → sprint loading.

- [ ] **Step 1: Rewrite HomeComponent**

Replace the full file content of `home.component.ts`:

```typescript
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { TuiIcon } from '@taiga-ui/core';
import {
  ActivityItem,
  DashboardService,
  DashboardStats,
  ProjectSummary,
  SprintProgress,
  TodayTask,
} from '../../services/dashboard.service';
import { UserService } from '../../services/user.service';

interface NavItem {
  label: string;
  icon: string;
  path: string;
}

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [DatePipe, RouterLink, TuiIcon],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss',
})
export class HomeComponent implements OnInit {
  private readonly dashboardService = inject(DashboardService);
  private readonly userService = inject(UserService);

  readonly today = new Date();

  readonly navItems: NavItem[] = [
    { label: 'Dashboard', icon: '@tui.layout-dashboard', path: '/home' },
    { label: 'My Tasks', icon: '@tui.check-square', path: '/tasks' },
    { label: 'Today', icon: '@tui.sun', path: '/today' },
    { label: 'Inbox', icon: '@tui.inbox', path: '/inbox' },
  ];

  readonly activeNav = signal<string>('/home');
  readonly currentUserName = signal<string>('');
  readonly workspaceName = signal<string>('');
  readonly workspacePlan = signal<string>('');
  readonly stats = signal<DashboardStats | null>(null);
  readonly todayTasks = signal<TodayTask[]>([]);
  readonly projects = signal<ProjectSummary[]>([]);
  readonly activity = signal<ActivityItem[]>([]);
  readonly activeSprint = signal<SprintProgress | null>(null);

  readonly greeting = computed(() => {
    const hour = this.today.getHours();
    const firstName = this.currentUserName().split(' ')[0] || '…';
    if (hour < 12) return `Good morning, ${firstName} 👋`;
    if (hour < 18) return `Good afternoon, ${firstName} 👋`;
    return `Good evening, ${firstName} 👋`;
  });

  readonly currentUserInitials = computed(() =>
    this.currentUserName()
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2) || '…'
  );

  readonly sprintProgressPct = computed(() => {
    const sprint = this.activeSprint();
    if (!sprint || sprint.storyPointsTotal === 0) return 0;
    return Math.round((sprint.storyPointsDone / sprint.storyPointsTotal) * 100);
  });

  readonly todayDueCount = computed(() =>
    this.todayTasks().filter(t => t.dueLabel === 'Today' && !t.done).length
  );

  ngOnInit(): void {
    // Load user profile
    this.userService.getCurrentUser().subscribe({
      next: user => this.currentUserName.set(user.display_name),
    });

    // Load stats, today's tasks, and activity in parallel
    this.dashboardService.getStats().subscribe({
      next: s => this.stats.set(s),
    });
    this.dashboardService.getTodayTasks().subscribe({
      next: t => this.todayTasks.set(t),
    });
    this.dashboardService.getActivity().subscribe({
      next: a => this.activity.set(a),
    });

    // Load workspaces → projects → sprint (sequential dependencies)
    this.dashboardService.getWorkspaces().subscribe({
      next: workspaces => {
        if (workspaces.length === 0) return;
        const workspace = workspaces[0];
        this.workspaceName.set(workspace.name);
        this.workspacePlan.set(`${workspace.plan} workspace`);

        this.dashboardService.getProjects(workspace.slug).subscribe({
          next: projects => {
            this.projects.set(projects);
            const sprintId = projects.find(p => p.activeSprintId)?.activeSprintId;
            if (sprintId) {
              this.dashboardService.getActiveSprint(sprintId).subscribe({
                next: s => this.activeSprint.set(s),
              });
            }
          },
        });
      },
    });
  }

  toggleTask(taskId: string): void {
    this.todayTasks.update(tasks =>
      tasks.map(t => (t.id === taskId ? { ...t, done: !t.done } : t))
    );
  }

  initials(name: string): string {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd dodoist-app && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add src/app/pages/home/home.component.ts src/app/services/dashboard.service.ts src/app/services/user.service.ts
git commit -m "feat: wire HomeComponent to live backend data"
```

---

## Task 9: End-to-end verification

- [ ] **Step 1: Run all backend tests**

```bash
cd dodoist-backend && source venv/bin/activate
pytest users/tests.py projects/tests.py tasks/tests.py -q
```
Expected: all PASS

- [ ] **Step 2: Run frontend type check**

```bash
cd dodoist-app && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 3: Start both servers**

```bash
# Terminal 1
cd dodoist-backend && source venv/bin/activate && python manage.py runserver

# Terminal 2
cd dodoist-app && npm start
```

- [ ] **Step 4: Create a test user and workspace via curl**

```bash
# Register
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"me@example.com","password":"testpass123","display_name":"Test User"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
echo "Token: $TOKEN"

# Create a workspace
curl -s -X POST http://localhost:8000/api/workspaces/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"My Workspace","slug":"my-workspace"}' | python3 -m json.tool
```

- [ ] **Step 5: Open browser and verify**

1. Go to `http://localhost:4200/signup` → register → should land on `/home`
2. Check the greeting shows your real name (not "Alice Johnson")
3. Workspace name in sidebar shows "My Workspace"
4. Stats, tasks, projects, activity sections render (empty arrays show empty state, no console errors)

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: home page now loads live data from backend"
```
