import pytest
from django.utils import timezone

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
