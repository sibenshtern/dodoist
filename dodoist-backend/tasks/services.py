from django.db import transaction
from django.utils import timezone

from projects.models import BoardColumn, Label, ProjectMember, ProjectRole, ProjectStatus, ProjectType, TaskStatus
from users.models import GlobalRole, User

from .models import (
    ActivityEntityType,
    ActivityLog,
    Comment,
    CustomField,
    DependencyType,
    Task,
    TaskAssignment,
    TaskCustomFieldValue,
    TaskDependency,
    TaskGuestAccess,
    TaskLabel,
    TaskPriority,
    TaskType,
)


def _log(actor: User, task: Task, action: str, old=None, new=None) -> None:
    ActivityLog.objects.create(
        entity_type=ActivityEntityType.TASK,
        entity_id=task.pk,
        actor=actor,
        action=action,
        old_value=old,
        new_value=new,
        project=task.project,
    )


# ---------------------------------------------------------------------------
# TaskService
# ---------------------------------------------------------------------------

class TaskService:
    @staticmethod
    @transaction.atomic
    def create_task(
        project,
        creator: User,
        title: str,
        task_type: str = TaskType.TASK,
        priority: str = TaskPriority.NONE,
        **kwargs,
    ) -> Task:
        if project.status != ProjectStatus.ACTIVE:
            raise ValueError("Cannot create tasks in an inactive project.")
        if not creator.has_elevated_access():
            if not ProjectMember.objects.filter(project=project, user=creator).exists():
                raise ValueError("Creator must be a project member.")

        task = Task.objects.create(
            project=project,
            created_by=creator,
            title=title,
            type=task_type,
            priority=priority,
            **kwargs,
        )
        _log(creator, task, "created", new={"title": title})
        return task

    @staticmethod
    def update_status(task: Task, new_status: str, actor: User) -> Task:
        if task.is_deleted():
            raise ValueError("Cannot update status of a deleted task.")
        if new_status not in TaskStatus.values:
            raise ValueError(f"Invalid status '{new_status}'. Choices: {TaskStatus.values}")

        old_status = task.status
        task.status = new_status

        if new_status == TaskStatus.DONE and not task.completed_at:
            task.completed_at = timezone.now()
        elif new_status != TaskStatus.DONE:
            task.completed_at = None

        task.save(update_fields=["status", "completed_at", "updated_at"])
        _log(actor, task, "status_changed", old={"status": old_status}, new={"status": new_status})
        return task

    @staticmethod
    def assign_user(task: Task, user: User, assigned_by: User) -> Task:
        if task.is_deleted():
            raise ValueError("Cannot assign a deleted task.")
        old = task.assigned_to_id
        task.assigned_to = user
        task.save(update_fields=["assigned_to", "updated_at"])
        _log(assigned_by, task, "assigned",
             old={"user_id": str(old)} if old else None,
             new={"user_id": str(user.pk)})
        return task

    @staticmethod
    def add_co_assignee(task: Task, user: User, assigned_by: User) -> TaskAssignment:
        assignment, _ = TaskAssignment.objects.get_or_create(
            task=task, user=user, defaults={"assigned_by": assigned_by}
        )
        return assignment

    @staticmethod
    def remove_co_assignee(task: Task, user: User) -> None:
        TaskAssignment.objects.filter(task=task, user=user).delete()

    @staticmethod
    def soft_delete(task: Task, actor: User) -> Task:
        if task.is_deleted():
            raise ValueError("Task is already deleted.")
        task.deleted_at = timezone.now()
        task.save(update_fields=["deleted_at", "updated_at"])
        _log(actor, task, "deleted")
        return task

    @staticmethod
    def restore(task: Task, actor: User) -> Task:
        if not task.is_deleted():
            raise ValueError("Task is not deleted.")
        task.deleted_at = None
        task.save(update_fields=["deleted_at", "updated_at"])
        _log(actor, task, "restored")
        return task

    @staticmethod
    def add_label(task: Task, label: Label) -> TaskLabel:
        obj, _ = TaskLabel.objects.get_or_create(task=task, label=label)
        return obj

    @staticmethod
    def remove_label(task: Task, label: Label) -> None:
        TaskLabel.objects.filter(task=task, label=label).delete()

    @staticmethod
    def add_dependency(task: Task, depends_on: Task, dep_type: str, created_by: User) -> TaskDependency:
        if task.pk == depends_on.pk:
            raise ValueError("A task cannot depend on itself.")
        if dep_type not in DependencyType.values:
            raise ValueError(f"Invalid dependency type '{dep_type}'.")
        return TaskDependency.objects.create(
            task=task, depends_on_task=depends_on, type=dep_type, created_by=created_by
        )

    @staticmethod
    def grant_guest_access(task: Task, user: User, granted_by: User) -> TaskGuestAccess:
        access, _ = TaskGuestAccess.objects.get_or_create(
            task=task, user=user, defaults={"granted_by": granted_by}
        )
        return access

    @staticmethod
    def set_custom_field_value(task: Task, field: CustomField, value: str) -> TaskCustomFieldValue:
        obj, _ = TaskCustomFieldValue.objects.update_or_create(
            task=task, custom_field=field, defaults={"value": value}
        )
        return obj

    @staticmethod
    def move_to_column(task: Task, column: BoardColumn, actor: User) -> Task:
        if task.is_deleted():
            raise ValueError("Cannot move a deleted task.")
        task.board_column = column
        task.status = column.status_mapping
        task.save(update_fields=["board_column", "status", "updated_at"])
        _log(actor, task, "moved", new={"column_id": str(column.pk), "status": column.status_mapping})
        return task


# ---------------------------------------------------------------------------
# CommentService
# ---------------------------------------------------------------------------

class CommentService:
    @staticmethod
    def add_comment(
        task: Task, author: User, body: dict, parent_comment: Comment | None = None
    ) -> Comment:
        if task.is_deleted():
            raise ValueError("Cannot comment on a deleted task.")
        comment = Comment.objects.create(
            task=task, author=author, body=body, parent_comment=parent_comment
        )
        _log(author, task, "commented", new={"comment_id": str(comment.pk)})
        return comment

    @staticmethod
    def edit_comment(comment: Comment, editor: User, new_body: dict) -> Comment:
        if comment.is_deleted():
            raise ValueError("Cannot edit a deleted comment.")
        if comment.author_id != editor.pk:
            raise ValueError("Only the author can edit this comment.")
        comment.body = new_body
        comment.is_edited = True
        comment.save(update_fields=["body", "is_edited", "updated_at"])
        return comment

    @staticmethod
    def soft_delete_comment(comment: Comment, actor: User) -> Comment:
        if comment.is_deleted():
            raise ValueError("Comment is already deleted.")
        comment.deleted_at = timezone.now()
        comment.save(update_fields=["deleted_at", "updated_at"])
        return comment


# ---------------------------------------------------------------------------
# AccessControlService
# ---------------------------------------------------------------------------

class AccessControlService:
    @staticmethod
    def can_view_task(user: User, task: Task) -> bool:
        if user.has_elevated_access():
            return True
        if task.is_deleted():
            return False

        membership = ProjectMember.objects.filter(project=task.project, user=user).first()

        if not membership:
            # No membership — only creator/assignee can see their own private tasks
            if task.is_private:
                return task.created_by_id == user.pk or task.assigned_to_id == user.pk
            return False

        if membership.role == ProjectRole.GU:
            if task.is_private:
                has_access = TaskGuestAccess.objects.filter(task=task, user=user).exists()
                return (
                    task.created_by_id == user.pk
                    or task.assigned_to_id == user.pk
                    or has_access
                )

        return True

    @staticmethod
    def can_edit_task(user: User, task: Task) -> bool:
        if user.has_elevated_access():
            return True
        if task.is_deleted():
            return False

        membership = ProjectMember.objects.filter(project=task.project, user=user).first()
        if not membership:
            return False

        role = membership.role

        if role in (ProjectRole.PO, ProjectRole.PM):
            return True

        if role == ProjectRole.DEV:
            is_creator = task.created_by_id == user.pk
            is_assignee = task.assigned_to_id == user.pk
            is_co_assignee = TaskAssignment.objects.filter(task=task, user=user).exists()
            return is_creator or is_assignee or is_co_assignee

        return False
