import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from projects.models import Label, ProjectMember, ProjectRole, ProjectStatus, ProjectType, TaskStatus
from projects.services import ProjectService, WorkspaceService
from tasks.models import (
    ActivityLog,
    Comment,
    CustomField,
    CustomFieldType,
    DependencyType,
    Task,
    TaskAssignment,
    TaskDependency,
    TaskGuestAccess,
    TaskLabel,
    TaskPriority,
    TaskType,
)
from tasks.services import AccessControlService, CommentService, TaskService
from users.models import GlobalRole, User
from users.services import UserService


@pytest.fixture
def user(db):
    return UserService.register(email="alice@example.com", password="pass123", display_name="Alice")


@pytest.fixture
def other_user(db):
    return UserService.register(email="bob@example.com", password="pass123", display_name="Bob")


@pytest.fixture
def workspace(user):
    return WorkspaceService.create_workspace(owner=user, name="Acme", slug="acme")


@pytest.fixture
def project(workspace, user):
    return ProjectService.create_project(workspace=workspace, creator=user, name="Alpha", key="ALP")


@pytest.fixture
def task(project, user):
    return TaskService.create_task(project=project, creator=user, title="Fix bug")


# ---------------------------------------------------------------------------
# TaskService
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTaskService:
    def test_create_task_defaults(self, project, user):
        task = TaskService.create_task(project=project, creator=user, title="My Task")
        assert task.title == "My Task"
        assert task.status == TaskStatus.BACKLOG
        assert task.type == TaskType.TASK
        assert task.priority == TaskPriority.NONE
        assert task.project_id == project.pk
        assert task.created_by_id == user.pk

    def test_create_task_logs_activity(self, project, user):
        task = TaskService.create_task(project=project, creator=user, title="Logged")
        assert ActivityLog.objects.filter(entity_id=task.pk, action="created").exists()

    def test_create_task_in_inactive_project_raises(self, project, user):
        ProjectService.archive_project(project)
        with pytest.raises(ValueError, match="inactive project"):
            TaskService.create_task(project=project, creator=user, title="X")

    def test_create_task_by_non_member_raises(self, project, other_user):
        with pytest.raises(ValueError, match="project member"):
            TaskService.create_task(project=project, creator=other_user, title="X")

    def test_create_task_by_elevated_user_without_membership(self, project, db):
        ga = User.objects.create_user(
            email="ga@example.com", password="p", display_name="GA", global_role=GlobalRole.GA
        )
        task = TaskService.create_task(project=project, creator=ga, title="GA Task")
        assert task.pk is not None

    def test_update_status(self, task, user):
        result = TaskService.update_status(task, TaskStatus.IN_PROGRESS, user)
        assert result.status == TaskStatus.IN_PROGRESS

    def test_update_status_to_done_sets_completed_at(self, task, user):
        result = TaskService.update_status(task, TaskStatus.DONE, user)
        assert result.completed_at is not None

    def test_update_status_from_done_clears_completed_at(self, task, user):
        TaskService.update_status(task, TaskStatus.DONE, user)
        result = TaskService.update_status(task, TaskStatus.IN_PROGRESS, user)
        assert result.completed_at is None

    def test_update_status_invalid_raises(self, task, user):
        with pytest.raises(ValueError, match="Invalid status"):
            TaskService.update_status(task, "flying", user)

    def test_update_status_on_deleted_task_raises(self, task, user):
        TaskService.soft_delete(task, user)
        with pytest.raises(ValueError, match="deleted task"):
            TaskService.update_status(task, TaskStatus.TODO, user)

    def test_update_status_logs_activity(self, task, user):
        TaskService.update_status(task, TaskStatus.TODO, user)
        assert ActivityLog.objects.filter(entity_id=task.pk, action="status_changed").exists()

    def test_assign_user(self, task, user, other_user):
        result = TaskService.assign_user(task, other_user, assigned_by=user)
        assert result.assigned_to_id == other_user.pk

    def test_assign_logs_activity(self, task, user, other_user):
        TaskService.assign_user(task, other_user, assigned_by=user)
        assert ActivityLog.objects.filter(entity_id=task.pk, action="assigned").exists()

    def test_assign_deleted_task_raises(self, task, user, other_user):
        TaskService.soft_delete(task, user)
        with pytest.raises(ValueError, match="deleted task"):
            TaskService.assign_user(task, other_user, assigned_by=user)

    def test_add_and_remove_co_assignee(self, task, user, other_user):
        assignment = TaskService.add_co_assignee(task, other_user, assigned_by=user)
        assert TaskAssignment.objects.filter(task=task, user=other_user).exists()
        TaskService.remove_co_assignee(task, other_user)
        assert not TaskAssignment.objects.filter(task=task, user=other_user).exists()

    def test_add_co_assignee_idempotent(self, task, user, other_user):
        a1 = TaskService.add_co_assignee(task, other_user, assigned_by=user)
        a2 = TaskService.add_co_assignee(task, other_user, assigned_by=user)
        assert a1.pk == a2.pk

    def test_soft_delete(self, task, user):
        result = TaskService.soft_delete(task, user)
        assert result.is_deleted() is True
        assert result.deleted_at is not None

    def test_soft_delete_twice_raises(self, task, user):
        TaskService.soft_delete(task, user)
        with pytest.raises(ValueError, match="already deleted"):
            TaskService.soft_delete(task, user)

    def test_restore(self, task, user):
        TaskService.soft_delete(task, user)
        result = TaskService.restore(task, user)
        assert result.is_deleted() is False

    def test_restore_non_deleted_raises(self, task, user):
        with pytest.raises(ValueError, match="not deleted"):
            TaskService.restore(task, user)

    def test_add_and_remove_label(self, workspace, task, user):
        label = Label.objects.create(workspace=workspace, name="Bug", color="#f00", created_by=user)
        TaskService.add_label(task, label)
        assert TaskLabel.objects.filter(task=task, label=label).exists()
        TaskService.remove_label(task, label)
        assert not TaskLabel.objects.filter(task=task, label=label).exists()

    def test_add_label_idempotent(self, workspace, task, user):
        label = Label.objects.create(workspace=workspace, name="Feat", color="#0f0", created_by=user)
        l1 = TaskService.add_label(task, label)
        l2 = TaskService.add_label(task, label)
        assert l1.pk == l2.pk

    def test_add_dependency(self, project, user):
        t1 = TaskService.create_task(project=project, creator=user, title="T1")
        t2 = TaskService.create_task(project=project, creator=user, title="T2")
        dep = TaskService.add_dependency(t1, t2, DependencyType.BLOCKS, created_by=user)
        assert dep.task_id == t1.pk
        assert dep.depends_on_task_id == t2.pk

    def test_add_self_dependency_raises(self, task, user):
        with pytest.raises(ValueError, match="depend on itself"):
            TaskService.add_dependency(task, task, DependencyType.BLOCKS, created_by=user)

    def test_add_dependency_invalid_type_raises(self, project, user):
        t1 = TaskService.create_task(project=project, creator=user, title="T1")
        t2 = TaskService.create_task(project=project, creator=user, title="T2")
        with pytest.raises(ValueError, match="Invalid dependency type"):
            TaskService.add_dependency(t1, t2, "OWNS", created_by=user)

    def test_grant_guest_access(self, task, user, other_user):
        access = TaskService.grant_guest_access(task, other_user, granted_by=user)
        assert TaskGuestAccess.objects.filter(task=task, user=other_user).exists()

    def test_set_custom_field_value(self, project, task, user):
        field = CustomField.objects.create(
            project=project, name="URL", field_type=CustomFieldType.URL, created_by=user
        )
        fv = TaskService.set_custom_field_value(task, field, "https://example.com")
        assert fv.value == "https://example.com"

    def test_set_custom_field_value_updates(self, project, task, user):
        field = CustomField.objects.create(
            project=project, name="Score", field_type=CustomFieldType.NUMBER, created_by=user
        )
        TaskService.set_custom_field_value(task, field, "10")
        fv = TaskService.set_custom_field_value(task, field, "20")
        assert fv.value == "20"

    def test_move_to_column(self, project, task, user):
        board = project.boards.get(is_default=True)
        col = board.columns.get(status_mapping=TaskStatus.TODO)
        result = TaskService.move_to_column(task, col, user)
        assert result.board_column_id == col.pk
        assert result.status == TaskStatus.TODO

    def test_move_deleted_task_raises(self, project, task, user):
        board = project.boards.get(is_default=True)
        col = board.columns.first()
        TaskService.soft_delete(task, user)
        with pytest.raises(ValueError, match="deleted task"):
            TaskService.move_to_column(task, col, user)


# ---------------------------------------------------------------------------
# Task model methods
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTaskModel:
    def test_is_overdue(self, task):
        task.due_date = timezone.now() - timezone.timedelta(days=1)
        task.save()
        assert task.is_overdue() is True

    def test_not_overdue_future(self, task):
        task.due_date = timezone.now() + timezone.timedelta(days=1)
        task.save()
        assert task.is_overdue() is False

    def test_not_overdue_when_done(self, task, user):
        task.due_date = timezone.now() - timezone.timedelta(days=1)
        task.save()
        TaskService.update_status(task, TaskStatus.DONE, user)
        task.refresh_from_db()
        assert task.is_overdue() is False

    def test_str(self, task):
        assert str(task) == "Fix bug"


# ---------------------------------------------------------------------------
# CommentService
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCommentService:
    def test_add_comment(self, task, user):
        body = {"type": "doc", "content": []}
        comment = CommentService.add_comment(task, user, body)
        assert comment.task_id == task.pk
        assert comment.author_id == user.pk

    def test_add_comment_logs_activity(self, task, user):
        CommentService.add_comment(task, user, {})
        assert ActivityLog.objects.filter(entity_id=task.pk, action="commented").exists()

    def test_add_comment_on_deleted_task_raises(self, task, user):
        TaskService.soft_delete(task, user)
        with pytest.raises(ValueError, match="deleted task"):
            CommentService.add_comment(task, user, {})

    def test_edit_comment(self, task, user):
        comment = CommentService.add_comment(task, user, {"text": "old"})
        updated = CommentService.edit_comment(comment, user, {"text": "new"})
        assert updated.body == {"text": "new"}
        assert updated.is_edited is True

    def test_edit_by_non_author_raises(self, task, user, other_user):
        comment = CommentService.add_comment(task, user, {})
        with pytest.raises(ValueError, match="Only the author"):
            CommentService.edit_comment(comment, other_user, {"text": "x"})

    def test_edit_deleted_comment_raises(self, task, user):
        comment = CommentService.add_comment(task, user, {})
        CommentService.soft_delete_comment(comment, user)
        with pytest.raises(ValueError, match="deleted comment"):
            CommentService.edit_comment(comment, user, {})

    def test_soft_delete_comment(self, task, user):
        comment = CommentService.add_comment(task, user, {})
        deleted = CommentService.soft_delete_comment(comment, user)
        assert deleted.is_deleted() is True

    def test_soft_delete_already_deleted_raises(self, task, user):
        comment = CommentService.add_comment(task, user, {})
        CommentService.soft_delete_comment(comment, user)
        with pytest.raises(ValueError, match="already deleted"):
            CommentService.soft_delete_comment(comment, user)

    def test_threaded_reply(self, task, user):
        parent = CommentService.add_comment(task, user, {"text": "parent"})
        reply = CommentService.add_comment(task, user, {"text": "reply"}, parent_comment=parent)
        assert reply.parent_comment_id == parent.pk


# ---------------------------------------------------------------------------
# AccessControlService
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAccessControlService:
    def test_elevated_user_can_view(self, task, db):
        ga = User.objects.create_user(
            email="ga@example.com", password="p", display_name="GA", global_role=GlobalRole.GA
        )
        assert AccessControlService.can_view_task(ga, task) is True

    def test_elevated_user_can_edit(self, task, db):
        sa = User.objects.create_user(
            email="sa@example.com", password="p", display_name="SA", global_role=GlobalRole.SA
        )
        assert AccessControlService.can_edit_task(sa, task) is True

    def test_deleted_task_not_viewable(self, task, user, other_user):
        TaskService.soft_delete(task, user)
        assert AccessControlService.can_view_task(other_user, task) is False

    def test_deleted_task_not_editable(self, task, user, other_user):
        TaskService.soft_delete(task, user)
        assert AccessControlService.can_edit_task(other_user, task) is False

    def test_non_member_cannot_view(self, task, other_user):
        assert AccessControlService.can_view_task(other_user, task) is False

    def test_non_member_cannot_edit(self, task, other_user):
        assert AccessControlService.can_edit_task(other_user, task) is False

    def test_project_member_can_view(self, workspace, project, task, other_user):
        WorkspaceService.add_member(workspace, other_user)
        ProjectService.add_member(project, other_user, ProjectRole.DEV)
        assert AccessControlService.can_view_task(other_user, task) is True

    def test_viewer_can_view_but_not_edit(self, workspace, project, task, other_user):
        WorkspaceService.add_member(workspace, other_user)
        ProjectService.add_member(project, other_user, ProjectRole.VW)
        assert AccessControlService.can_view_task(other_user, task) is True
        assert AccessControlService.can_edit_task(other_user, task) is False

    def test_guest_cannot_edit(self, workspace, project, task, other_user):
        WorkspaceService.add_member(workspace, other_user)
        ProjectService.add_member(project, other_user, ProjectRole.GU)
        assert AccessControlService.can_edit_task(other_user, task) is False

    def test_po_can_edit_any_task(self, task, user):
        assert AccessControlService.can_edit_task(user, task) is True

    def test_pm_can_edit_any_task(self, workspace, project, task, other_user):
        WorkspaceService.add_member(workspace, other_user)
        ProjectService.add_member(project, other_user, ProjectRole.PM)
        assert AccessControlService.can_edit_task(other_user, task) is True

    def test_dev_can_edit_own_task(self, workspace, project, other_user, db):
        WorkspaceService.add_member(workspace, other_user)
        ProjectService.add_member(project, other_user, ProjectRole.DEV)
        own = TaskService.create_task(project=project, creator=other_user, title="Own")
        assert AccessControlService.can_edit_task(other_user, own) is True

    def test_dev_cannot_edit_unrelated_task(self, workspace, project, task, other_user):
        WorkspaceService.add_member(workspace, other_user)
        ProjectService.add_member(project, other_user, ProjectRole.DEV)
        assert AccessControlService.can_edit_task(other_user, task) is False

    def test_dev_can_edit_assigned_task(self, workspace, project, task, user, other_user):
        WorkspaceService.add_member(workspace, other_user)
        ProjectService.add_member(project, other_user, ProjectRole.DEV)
        TaskService.assign_user(task, other_user, assigned_by=user)
        assert AccessControlService.can_edit_task(other_user, task) is True

    def test_dev_can_edit_co_assigned_task(self, workspace, project, task, user, other_user):
        WorkspaceService.add_member(workspace, other_user)
        ProjectService.add_member(project, other_user, ProjectRole.DEV)
        TaskService.add_co_assignee(task, other_user, assigned_by=user)
        assert AccessControlService.can_edit_task(other_user, task) is True

    def test_guest_cannot_view_private_task_without_access(self, workspace, project, user, other_user):
        WorkspaceService.add_member(workspace, other_user)
        ProjectService.add_member(project, other_user, ProjectRole.GU)
        private_task = Task.objects.create(
            project=project, created_by=user, title="Private",
            status=TaskStatus.BACKLOG, is_private=True,
        )
        assert AccessControlService.can_view_task(other_user, private_task) is False

    def test_guest_can_view_task_with_access_grant(self, workspace, project, user, other_user):
        WorkspaceService.add_member(workspace, other_user)
        ProjectService.add_member(project, other_user, ProjectRole.GU)
        private_task = Task.objects.create(
            project=project, created_by=user, title="Private",
            status=TaskStatus.BACKLOG, is_private=True,
        )
        TaskService.grant_guest_access(private_task, other_user, granted_by=user)
        assert AccessControlService.can_view_task(other_user, private_task) is True


# ===========================================================================
# Shared fixtures for view tests
# ===========================================================================

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def sa_user(db):
    return User.objects.create_user(
        email="sa@example.com", password="pass123", display_name="SA",
        global_role=GlobalRole.SA,
    )


@pytest.fixture
def pm_user(db, workspace, project):
    u = UserService.register(email="pm@example.com", password="pass123", display_name="PM")
    WorkspaceService.add_member(workspace, u)
    ProjectService.add_member(project, u, ProjectRole.PM)
    return u


@pytest.fixture
def dev_user(db, workspace, project):
    u = UserService.register(email="dev@example.com", password="pass123", display_name="Dev")
    WorkspaceService.add_member(workspace, u)
    ProjectService.add_member(project, u, ProjectRole.DEV)
    return u


@pytest.fixture
def viewer_user(db, workspace, project):
    u = UserService.register(email="viewer@example.com", password="pass123", display_name="Viewer")
    WorkspaceService.add_member(workspace, u)
    ProjectService.add_member(project, u, ProjectRole.VW)
    return u


@pytest.fixture
def guest_user(db, workspace, project):
    u = UserService.register(email="guest@example.com", password="pass123", display_name="Guest")
    WorkspaceService.add_member(workspace, u)
    ProjectService.add_member(project, u, ProjectRole.GU)
    return u


@pytest.fixture
def label(workspace, user):
    return Label.objects.create(workspace=workspace, name="bug", color="#ff0000", created_by=user)


# ===========================================================================
# API: ProjectTaskListCreateView  GET /api/projects/<pk>/tasks/
# ===========================================================================

@pytest.mark.django_db
class TestProjectTaskListView:
    def url(self, project):
        return f"/api/projects/{project.pk}/tasks/"

    def test_unauthenticated_returns_401(self, api_client, project):
        response = api_client.get(self.url(project))
        assert response.status_code == 401

    def test_member_can_list_tasks(self, auth_client, project, task):
        response = auth_client.get(self.url(project))
        assert response.status_code == 200
        assert any(str(task.pk) == t["id"] for t in response.data)

    def test_non_member_gets_404(self, api_client, project, other_user):
        api_client.force_authenticate(user=other_user)
        response = api_client.get(self.url(project))
        assert response.status_code == 404

    def test_sa_can_list_without_membership(self, api_client, sa_user, project, task):
        api_client.force_authenticate(user=sa_user)
        response = api_client.get(self.url(project))
        assert response.status_code == 200

    def test_deleted_tasks_excluded(self, auth_client, project, task, user):
        TaskService.soft_delete(task, user)
        response = auth_client.get(self.url(project))
        assert response.status_code == 200
        assert not any(str(task.pk) == t["id"] for t in response.data)

    def test_status_filter_single(self, auth_client, project, task, user):
        TaskService.update_status(task, TaskStatus.IN_PROGRESS, user)
        response = auth_client.get(self.url(project), {"status": "in_progress"})
        assert response.status_code == 200
        assert all(t["status"] == "in_progress" for t in response.data)

    def test_status_filter_comma_separated(self, auth_client, project, user):
        t1 = TaskService.create_task(project=project, creator=user, title="T1")
        t2 = TaskService.create_task(project=project, creator=user, title="T2")
        TaskService.update_status(t1, TaskStatus.TODO, user)
        TaskService.update_status(t2, TaskStatus.IN_PROGRESS, user)
        response = auth_client.get(self.url(project), {"status": "todo,in_progress"})
        assert response.status_code == 200
        returned_statuses = {t["status"] for t in response.data}
        assert returned_statuses <= {"todo", "in_progress"}

    def test_priority_filter_comma_separated(self, auth_client, project, user):
        TaskService.create_task(project=project, creator=user, title="Hi", priority=TaskPriority.HIGH)
        TaskService.create_task(project=project, creator=user, title="Lo", priority=TaskPriority.LOW)
        response = auth_client.get(self.url(project), {"priority": "high,low"})
        assert response.status_code == 200
        returned_priorities = {t["priority"] for t in response.data}
        assert returned_priorities <= {"high", "low"}

    def test_assigned_to_filter(self, auth_client, project, task, user, other_user):
        WorkspaceService.add_member(task.project.workspace, other_user)
        ProjectService.add_member(project, other_user, ProjectRole.DEV)
        TaskService.assign_user(task, other_user, assigned_by=user)
        response = auth_client.get(self.url(project), {"assigned_to": str(other_user.pk)})
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["id"] == str(task.pk)

    def test_search_filter(self, auth_client, project, user):
        TaskService.create_task(project=project, creator=user, title="OAuth login")
        TaskService.create_task(project=project, creator=user, title="Fix styling")
        response = auth_client.get(self.url(project), {"search": "OAuth"})
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["title"] == "OAuth login"

    def test_parent_task_id_null_returns_root_tasks(self, auth_client, project, task, user):
        subtask = TaskService.create_task(project=project, creator=user, title="Sub", parent_task=task)
        response = auth_client.get(self.url(project), {"parent_task_id": "null"})
        assert response.status_code == 200
        returned_ids = {t["id"] for t in response.data}
        assert str(task.pk) in returned_ids
        assert str(subtask.pk) not in returned_ids

    def test_parent_task_id_filter_returns_subtasks(self, auth_client, project, task, user):
        subtask = TaskService.create_task(project=project, creator=user, title="Sub", parent_task=task)
        other = TaskService.create_task(project=project, creator=user, title="Other")
        response = auth_client.get(self.url(project), {"parent_task_id": str(task.pk)})
        assert response.status_code == 200
        returned_ids = {t["id"] for t in response.data}
        assert str(subtask.pk) in returned_ids
        assert str(other.pk) not in returned_ids

    def test_label_ids_filter(self, auth_client, project, task, label):
        TaskService.add_label(task, label)
        other = TaskService.create_task(project=task.project, creator=task.created_by, title="No label")
        response = auth_client.get(self.url(project), {"label_ids": str(label.pk)})
        assert response.status_code == 200
        returned_ids = {t["id"] for t in response.data}
        assert str(task.pk) in returned_ids
        assert str(other.pk) not in returned_ids

    def test_sort_dir_desc(self, auth_client, project, user):
        t1 = TaskService.create_task(project=project, creator=user, title="First")
        t2 = TaskService.create_task(project=project, creator=user, title="Second")
        response = auth_client.get(self.url(project), {"sort_by": "created_at", "sort_dir": "desc"})
        assert response.status_code == 200
        ids = [t["id"] for t in response.data]
        assert ids.index(str(t2.pk)) < ids.index(str(t1.pk))

    def test_invalid_sort_by_still_returns_200(self, auth_client, project):
        response = auth_client.get(self.url(project), {"sort_by": "injected_field"})
        assert response.status_code == 200

    def test_guest_cannot_see_private_tasks(self, api_client, project, task, guest_user, user):
        task.is_private = True
        task.save(update_fields=["is_private"])
        api_client.force_authenticate(user=guest_user)
        response = api_client.get(self.url(project))
        assert response.status_code == 200
        assert not any(str(task.pk) == t["id"] for t in response.data)

    def test_nonexistent_project_returns_404(self, auth_client):
        response = auth_client.get("/api/projects/00000000-0000-0000-0000-000000000000/tasks/")
        assert response.status_code == 404


# ===========================================================================
# API: ProjectTaskListCreateView  POST /api/projects/<pk>/tasks/
# ===========================================================================

@pytest.mark.django_db
class TestProjectTaskCreateView:
    def url(self, project):
        return f"/api/projects/{project.pk}/tasks/"

    def test_unauthenticated_returns_401(self, api_client, project):
        response = api_client.post(self.url(project), {"title": "X"})
        assert response.status_code == 401

    def test_po_can_create_task(self, auth_client, project):
        response = auth_client.post(self.url(project), {"title": "New task", "task_type": "task", "priority": "none"})
        assert response.status_code == 201
        assert response.data["title"] == "New task"
        assert str(response.data["project"]) == str(project.pk)

    def test_dev_can_create_task(self, api_client, project, dev_user):
        api_client.force_authenticate(user=dev_user)
        response = api_client.post(self.url(project), {"title": "Dev task", "task_type": "bug", "priority": "high"})
        assert response.status_code == 201

    def test_viewer_cannot_create_task(self, api_client, project, viewer_user):
        api_client.force_authenticate(user=viewer_user)
        response = api_client.post(self.url(project), {"title": "X"})
        assert response.status_code == 403

    def test_guest_cannot_create_task(self, api_client, project, guest_user):
        api_client.force_authenticate(user=guest_user)
        response = api_client.post(self.url(project), {"title": "X"})
        assert response.status_code == 403

    def test_non_member_gets_404(self, api_client, project, other_user):
        api_client.force_authenticate(user=other_user)
        response = api_client.post(self.url(project), {"title": "X"})
        assert response.status_code == 404

    def test_missing_title_returns_400(self, auth_client, project):
        response = auth_client.post(self.url(project), {"priority": "high"})
        assert response.status_code == 400

    def test_create_subtask_with_parent_task_id(self, auth_client, project, task):
        response = auth_client.post(self.url(project), {"title": "Sub", "parent_task_id": str(task.pk)})
        assert response.status_code == 201
        assert str(response.data["parent_task"]) == str(task.pk)

    def test_invalid_parent_task_id_returns_400(self, auth_client, project):
        response = auth_client.post(
            self.url(project), {"title": "X", "parent_task_id": "00000000-0000-0000-0000-000000000000"}
        )
        assert response.status_code == 400

    def test_sa_can_create_without_membership(self, api_client, sa_user, project):
        api_client.force_authenticate(user=sa_user)
        response = api_client.post(self.url(project), {"title": "SA task"})
        assert response.status_code == 201

    def test_inactive_project_returns_400(self, auth_client, project, user):
        ProjectService.archive_project(project)
        response = auth_client.post(self.url(project), {"title": "X"})
        assert response.status_code == 400


# ===========================================================================
# API: TaskSubtaskListView  GET /api/tasks/<pk>/subtasks/
# ===========================================================================

@pytest.mark.django_db
class TestTaskSubtaskListView:
    def url(self, task):
        return f"/api/tasks/{task.pk}/subtasks/"

    def test_unauthenticated_returns_401(self, api_client, task):
        response = api_client.get(self.url(task))
        assert response.status_code == 401

    def test_member_can_list_subtasks(self, auth_client, project, task, user):
        subtask = TaskService.create_task(project=project, creator=user, title="Sub", parent_task=task)
        response = auth_client.get(self.url(task))
        assert response.status_code == 200
        assert any(str(subtask.pk) == t["id"] for t in response.data)

    def test_top_level_tasks_excluded(self, auth_client, project, task, user):
        other = TaskService.create_task(project=project, creator=user, title="Other")
        response = auth_client.get(self.url(task))
        assert response.status_code == 200
        assert not any(str(other.pk) == t["id"] for t in response.data)

    def test_deleted_subtasks_excluded(self, auth_client, project, task, user):
        subtask = TaskService.create_task(project=project, creator=user, title="Sub", parent_task=task)
        TaskService.soft_delete(subtask, user)
        response = auth_client.get(self.url(task))
        assert response.status_code == 200
        assert not any(str(subtask.pk) == t["id"] for t in response.data)

    def test_status_filter(self, auth_client, project, task, user):
        s1 = TaskService.create_task(project=project, creator=user, title="S1", parent_task=task)
        s2 = TaskService.create_task(project=project, creator=user, title="S2", parent_task=task)
        TaskService.update_status(s1, TaskStatus.DONE, user)
        response = auth_client.get(self.url(task), {"status": "done"})
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["id"] == str(s1.pk)

    def test_non_member_gets_404(self, api_client, task, other_user):
        api_client.force_authenticate(user=other_user)
        response = api_client.get(self.url(task))
        assert response.status_code == 404

    def test_nonexistent_task_returns_404(self, auth_client):
        response = auth_client.get("/api/tasks/00000000-0000-0000-0000-000000000000/subtasks/")
        assert response.status_code == 404


# ===========================================================================
# API: TaskAssignmentListView  POST /api/tasks/<pk>/assignments/
# ===========================================================================

@pytest.mark.django_db
class TestTaskAssignmentListView:
    def url(self, task):
        return f"/api/tasks/{task.pk}/assignments/"

    def test_unauthenticated_returns_401(self, api_client, task):
        response = api_client.post(self.url(task), {"user_id": "00000000-0000-0000-0000-000000000000"})
        assert response.status_code == 401

    def test_po_can_add_co_assignee(self, auth_client, task, dev_user):
        response = auth_client.post(self.url(task), {"user_id": str(dev_user.pk)})
        assert response.status_code == 201
        assert TaskAssignment.objects.filter(task=task, user=dev_user).exists()

    def test_pm_can_add_co_assignee(self, api_client, task, pm_user, dev_user):
        api_client.force_authenticate(user=pm_user)
        response = api_client.post(self.url(task), {"user_id": str(dev_user.pk)})
        assert response.status_code == 201

    def test_viewer_cannot_add_co_assignee(self, api_client, task, viewer_user, dev_user):
        api_client.force_authenticate(user=viewer_user)
        response = api_client.post(self.url(task), {"user_id": str(dev_user.pk)})
        assert response.status_code == 403

    def test_unknown_user_returns_400(self, auth_client, task):
        response = auth_client.post(self.url(task), {"user_id": "00000000-0000-0000-0000-000000000000"})
        assert response.status_code == 400

    def test_response_contains_assignment_fields(self, auth_client, task, dev_user):
        response = auth_client.post(self.url(task), {"user_id": str(dev_user.pk)})
        assert response.status_code == 201
        assert "id" in response.data
        assert response.data["user"]["id"] == str(dev_user.pk)

    def test_idempotent_add_returns_existing(self, auth_client, task, dev_user):
        r1 = auth_client.post(self.url(task), {"user_id": str(dev_user.pk)})
        r2 = auth_client.post(self.url(task), {"user_id": str(dev_user.pk)})
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert TaskAssignment.objects.filter(task=task, user=dev_user).count() == 1


# ===========================================================================
# API: TaskAssignmentDetailView  DELETE /api/tasks/<pk>/assignments/<user_id>/
# ===========================================================================

@pytest.mark.django_db
class TestTaskAssignmentDetailView:
    def url(self, task, user_id):
        return f"/api/tasks/{task.pk}/assignments/{user_id}/"

    def test_unauthenticated_returns_401(self, api_client, task, dev_user):
        response = api_client.delete(self.url(task, dev_user.pk))
        assert response.status_code == 401

    def test_po_can_remove_co_assignee(self, auth_client, task, user, dev_user):
        TaskService.add_co_assignee(task, dev_user, assigned_by=user)
        response = auth_client.delete(self.url(task, dev_user.pk))
        assert response.status_code == 204
        assert not TaskAssignment.objects.filter(task=task, user=dev_user).exists()

    def test_viewer_cannot_remove_co_assignee(self, api_client, task, user, viewer_user, dev_user):
        TaskService.add_co_assignee(task, dev_user, assigned_by=user)
        api_client.force_authenticate(user=viewer_user)
        response = api_client.delete(self.url(task, dev_user.pk))
        assert response.status_code == 403

    def test_nonexistent_user_returns_404(self, auth_client, task):
        response = auth_client.delete(self.url(task, "00000000-0000-0000-0000-000000000000"))
        assert response.status_code == 404

    def test_remove_non_assigned_user_returns_204(self, auth_client, task, dev_user):
        # Removing a user who was never assigned is a no-op, not an error
        response = auth_client.delete(self.url(task, dev_user.pk))
        assert response.status_code == 204


# ===========================================================================
# API: TaskLabelListView  POST /api/tasks/<pk>/labels/
# ===========================================================================

@pytest.mark.django_db
class TestTaskLabelListView:
    def url(self, task):
        return f"/api/tasks/{task.pk}/labels/"

    def test_unauthenticated_returns_401(self, api_client, task, label):
        response = api_client.post(self.url(task), {"label_id": str(label.pk)})
        assert response.status_code == 401

    def test_po_can_attach_label(self, auth_client, task, label):
        response = auth_client.post(self.url(task), {"label_id": str(label.pk)})
        assert response.status_code == 201
        assert TaskLabel.objects.filter(task=task, label=label).exists()

    def test_pm_can_attach_label(self, api_client, task, label, pm_user):
        api_client.force_authenticate(user=pm_user)
        response = api_client.post(self.url(task), {"label_id": str(label.pk)})
        assert response.status_code == 201

    def test_viewer_cannot_attach_label(self, api_client, task, label, viewer_user):
        api_client.force_authenticate(user=viewer_user)
        response = api_client.post(self.url(task), {"label_id": str(label.pk)})
        assert response.status_code == 403

    def test_unknown_label_returns_400(self, auth_client, task):
        response = auth_client.post(self.url(task), {"label_id": "00000000-0000-0000-0000-000000000000"})
        assert response.status_code == 400

    def test_idempotent_attach(self, auth_client, task, label):
        auth_client.post(self.url(task), {"label_id": str(label.pk)})
        auth_client.post(self.url(task), {"label_id": str(label.pk)})
        assert TaskLabel.objects.filter(task=task, label=label).count() == 1


# ===========================================================================
# API: TaskLabelDetailView  DELETE /api/tasks/<pk>/labels/<label_id>/
# ===========================================================================

@pytest.mark.django_db
class TestTaskLabelDetailView:
    def url(self, task, label_id):
        return f"/api/tasks/{task.pk}/labels/{label_id}/"

    def test_unauthenticated_returns_401(self, api_client, task, label):
        response = api_client.delete(self.url(task, label.pk))
        assert response.status_code == 401

    def test_po_can_detach_label(self, auth_client, task, label, user):
        TaskService.add_label(task, label)
        response = auth_client.delete(self.url(task, label.pk))
        assert response.status_code == 204
        assert not TaskLabel.objects.filter(task=task, label=label).exists()

    def test_viewer_cannot_detach_label(self, api_client, task, label, user, viewer_user):
        TaskService.add_label(task, label)
        api_client.force_authenticate(user=viewer_user)
        response = api_client.delete(self.url(task, label.pk))
        assert response.status_code == 403

    def test_nonexistent_label_returns_404(self, auth_client, task):
        response = auth_client.delete(self.url(task, "00000000-0000-0000-0000-000000000000"))
        assert response.status_code == 404

    def test_detach_unattached_label_returns_204(self, auth_client, task, label):
        # Removing a label that's not attached is a no-op
        response = auth_client.delete(self.url(task, label.pk))
        assert response.status_code == 204


# ===========================================================================
# API: TaskDependencyListView  GET/POST /api/tasks/<pk>/dependencies/
# ===========================================================================

@pytest.mark.django_db
class TestTaskDependencyListView:
    def url(self, task):
        return f"/api/tasks/{task.pk}/dependencies/"

    def test_unauthenticated_returns_401(self, api_client, task):
        response = api_client.get(self.url(task))
        assert response.status_code == 401

    def test_member_can_list_dependencies(self, auth_client, project, task, user):
        t2 = TaskService.create_task(project=project, creator=user, title="T2")
        TaskService.add_dependency(task, t2, DependencyType.BLOCKS, created_by=user)
        response = auth_client.get(self.url(task))
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["type"] == DependencyType.BLOCKS

    def test_non_member_gets_404(self, api_client, task, other_user):
        api_client.force_authenticate(user=other_user)
        response = api_client.get(self.url(task))
        assert response.status_code == 404

    def test_response_contains_expected_fields(self, auth_client, project, task, user):
        t2 = TaskService.create_task(project=project, creator=user, title="T2")
        TaskService.add_dependency(task, t2, DependencyType.RELATES_TO, created_by=user)
        response = auth_client.get(self.url(task))
        dep = response.data[0]
        assert "id" in dep
        assert "depends_on_task" in dep
        assert dep["depends_on_task"]["id"] == str(t2.pk)
        assert "created_by" in dep
        assert "created_at" in dep

    def test_po_can_add_dependency(self, auth_client, project, task, user):
        t2 = TaskService.create_task(project=project, creator=user, title="T2")
        response = auth_client.post(
            self.url(task), {"depends_on_task_id": str(t2.pk), "type": DependencyType.BLOCKS}
        )
        assert response.status_code == 201
        assert TaskDependency.objects.filter(task=task, depends_on_task=t2).exists()

    def test_viewer_cannot_add_dependency(self, api_client, project, task, user, viewer_user):
        t2 = TaskService.create_task(project=project, creator=user, title="T2")
        api_client.force_authenticate(user=viewer_user)
        response = api_client.post(
            self.url(task), {"depends_on_task_id": str(t2.pk), "type": DependencyType.BLOCKS}
        )
        assert response.status_code == 403

    def test_self_dependency_returns_400(self, auth_client, task):
        response = auth_client.post(
            self.url(task), {"depends_on_task_id": str(task.pk), "type": DependencyType.BLOCKS}
        )
        assert response.status_code == 400

    def test_unknown_task_returns_400(self, auth_client, task):
        response = auth_client.post(
            self.url(task),
            {"depends_on_task_id": "00000000-0000-0000-0000-000000000000", "type": DependencyType.BLOCKS},
        )
        assert response.status_code == 400

    def test_invalid_type_returns_400(self, auth_client, project, task, user):
        t2 = TaskService.create_task(project=project, creator=user, title="T2")
        response = auth_client.post(
            self.url(task), {"depends_on_task_id": str(t2.pk), "type": "owns"}
        )
        assert response.status_code == 400

    def test_missing_type_returns_400(self, auth_client, project, task, user):
        t2 = TaskService.create_task(project=project, creator=user, title="T2")
        response = auth_client.post(self.url(task), {"depends_on_task_id": str(t2.pk)})
        assert response.status_code == 400


# ===========================================================================
# API: TaskDependencyDetailView  DELETE /api/tasks/<pk>/dependencies/<dep_id>/
# ===========================================================================

@pytest.mark.django_db
class TestTaskDependencyDetailView:
    def url(self, task, dep_id):
        return f"/api/tasks/{task.pk}/dependencies/{dep_id}/"

    def test_unauthenticated_returns_401(self, api_client, task):
        response = api_client.delete(self.url(task, "00000000-0000-0000-0000-000000000000"))
        assert response.status_code == 401

    def test_po_can_remove_dependency(self, auth_client, project, task, user):
        t2 = TaskService.create_task(project=project, creator=user, title="T2")
        dep = TaskService.add_dependency(task, t2, DependencyType.BLOCKS, created_by=user)
        response = auth_client.delete(self.url(task, dep.pk))
        assert response.status_code == 204
        assert not TaskDependency.objects.filter(pk=dep.pk).exists()

    def test_viewer_cannot_remove_dependency(self, api_client, project, task, user, viewer_user):
        t2 = TaskService.create_task(project=project, creator=user, title="T2")
        dep = TaskService.add_dependency(task, t2, DependencyType.BLOCKS, created_by=user)
        api_client.force_authenticate(user=viewer_user)
        response = api_client.delete(self.url(task, dep.pk))
        assert response.status_code == 403

    def test_nonexistent_dependency_returns_404(self, auth_client, task):
        response = auth_client.delete(self.url(task, "00000000-0000-0000-0000-000000000000"))
        assert response.status_code == 404

    def test_dependency_of_other_task_returns_404(self, auth_client, project, task, user):
        t2 = TaskService.create_task(project=project, creator=user, title="T2")
        t3 = TaskService.create_task(project=project, creator=user, title="T3")
        dep = TaskService.add_dependency(t2, t3, DependencyType.BLOCKS, created_by=user)
        response = auth_client.delete(self.url(task, dep.pk))
        assert response.status_code == 404


# ===========================================================================
# API: TaskGuestAccessListView  GET/POST /api/tasks/<pk>/guest-access/
# ===========================================================================

@pytest.mark.django_db
class TestTaskGuestAccessListView:
    def url(self, task):
        return f"/api/tasks/{task.pk}/guest-access/"

    def test_unauthenticated_returns_401(self, api_client, task):
        response = api_client.get(self.url(task))
        assert response.status_code == 401

    def test_po_can_list_guest_accesses(self, auth_client, task, guest_user, user):
        TaskService.grant_guest_access(task, guest_user, granted_by=user)
        response = auth_client.get(self.url(task))
        assert response.status_code == 200
        assert any(a["user"]["id"] == str(guest_user.pk) for a in response.data)

    def test_pm_can_list_guest_accesses(self, api_client, task, pm_user, guest_user, user):
        TaskService.grant_guest_access(task, guest_user, granted_by=user)
        api_client.force_authenticate(user=pm_user)
        response = api_client.get(self.url(task))
        assert response.status_code == 200

    def test_dev_cannot_list_guest_accesses(self, api_client, task, dev_user):
        api_client.force_authenticate(user=dev_user)
        response = api_client.get(self.url(task))
        assert response.status_code == 403

    def test_sa_can_list_guest_accesses(self, api_client, sa_user, task, guest_user, user):
        TaskService.grant_guest_access(task, guest_user, granted_by=user)
        api_client.force_authenticate(user=sa_user)
        response = api_client.get(self.url(task))
        assert response.status_code == 200

    def test_response_contains_expected_fields(self, auth_client, task, guest_user, user):
        TaskService.grant_guest_access(task, guest_user, granted_by=user)
        response = auth_client.get(self.url(task))
        access = response.data[0]
        assert "id" in access
        assert "user" in access
        assert "granted_by" in access
        assert "granted_at" in access
        assert "expires_at" in access

    def test_po_can_grant_access(self, auth_client, task, guest_user):
        response = auth_client.post(self.url(task), {"user_id": str(guest_user.pk)})
        assert response.status_code == 201
        assert TaskGuestAccess.objects.filter(task=task, user=guest_user).exists()

    def test_pm_can_grant_access(self, api_client, task, pm_user, guest_user):
        api_client.force_authenticate(user=pm_user)
        response = api_client.post(self.url(task), {"user_id": str(guest_user.pk)})
        assert response.status_code == 201

    def test_dev_cannot_grant_access(self, api_client, task, dev_user, guest_user):
        api_client.force_authenticate(user=dev_user)
        response = api_client.post(self.url(task), {"user_id": str(guest_user.pk)})
        assert response.status_code == 403

    def test_grant_with_expires_at(self, auth_client, task, guest_user):
        expires = "2099-12-31T23:59:59Z"
        response = auth_client.post(self.url(task), {"user_id": str(guest_user.pk), "expires_at": expires})
        assert response.status_code == 201
        assert response.data["expires_at"] is not None
        access = TaskGuestAccess.objects.get(task=task, user=guest_user)
        assert access.expires_at is not None

    def test_unknown_user_returns_400(self, auth_client, task):
        response = auth_client.post(self.url(task), {"user_id": "00000000-0000-0000-0000-000000000000"})
        assert response.status_code == 400

    def test_idempotent_grant(self, auth_client, task, guest_user):
        auth_client.post(self.url(task), {"user_id": str(guest_user.pk)})
        auth_client.post(self.url(task), {"user_id": str(guest_user.pk)})
        assert TaskGuestAccess.objects.filter(task=task, user=guest_user).count() == 1


# ===========================================================================
# API: TaskGuestAccessDetailView  DELETE /api/tasks/<pk>/guest-access/<user_id>/
# ===========================================================================

@pytest.mark.django_db
class TestTaskGuestAccessDetailView:
    def url(self, task, user_id):
        return f"/api/tasks/{task.pk}/guest-access/{user_id}/"

    def test_unauthenticated_returns_401(self, api_client, task, guest_user):
        response = api_client.delete(self.url(task, guest_user.pk))
        assert response.status_code == 401

    def test_po_can_revoke_access(self, auth_client, task, guest_user, user):
        TaskService.grant_guest_access(task, guest_user, granted_by=user)
        response = auth_client.delete(self.url(task, guest_user.pk))
        assert response.status_code == 204
        assert not TaskGuestAccess.objects.filter(task=task, user=guest_user).exists()

    def test_pm_can_revoke_access(self, api_client, task, pm_user, guest_user, user):
        TaskService.grant_guest_access(task, guest_user, granted_by=user)
        api_client.force_authenticate(user=pm_user)
        response = api_client.delete(self.url(task, guest_user.pk))
        assert response.status_code == 204

    def test_dev_cannot_revoke_access(self, api_client, task, dev_user, guest_user, user):
        TaskService.grant_guest_access(task, guest_user, granted_by=user)
        api_client.force_authenticate(user=dev_user)
        response = api_client.delete(self.url(task, guest_user.pk))
        assert response.status_code == 403

    def test_sa_can_revoke_access(self, api_client, sa_user, task, guest_user, user):
        TaskService.grant_guest_access(task, guest_user, granted_by=user)
        api_client.force_authenticate(user=sa_user)
        response = api_client.delete(self.url(task, guest_user.pk))
        assert response.status_code == 204

    def test_revoke_nonexistent_access_returns_204(self, auth_client, task, guest_user):
        # Revoking access that was never granted is a no-op
        response = auth_client.delete(self.url(task, guest_user.pk))
        assert response.status_code == 204
