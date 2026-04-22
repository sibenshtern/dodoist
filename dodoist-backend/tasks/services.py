import os
import re
import uuid as _uuid

from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from projects.models import BoardColumn, Label, ProjectMember, ProjectRole, ProjectStatus, ProjectType, TaskStatus
from users.models import GlobalRole, NotificationType, User

from .models import (
    ActivityEntityType,
    ActivityLog,
    Attachment,
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


def _has_dependency_cycle(task: Task, depends_on: Task) -> bool:
    """Return True if adding task→depends_on would create a cycle (iterative DFS)."""
    visited: set = set()
    stack = [depends_on.pk]
    while stack:
        current = stack.pop()
        if current == task.pk:
            return True
        if current in visited:
            continue
        visited.add(current)
        neighbors = TaskDependency.objects.filter(
            task_id=current
        ).values_list("depends_on_task_id", flat=True)
        stack.extend(neighbors)
    return False


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
    @transaction.atomic
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

        from users.services import NotificationService
        NotificationService.notify_watchers(
            task=task,
            notification_type=NotificationType.STATUS_CHANGED,
            message=f"{actor.display_name} changed status of '{task.title}' to {new_status}",
            actor=actor,
        )
        return task

    @staticmethod
    @transaction.atomic
    def assign_user(task: Task, user: User, assigned_by: User) -> Task:
        if task.is_deleted():
            raise ValueError("Cannot assign a deleted task.")
        old = task.assigned_to_id
        task.assigned_to = user
        task.save(update_fields=["assigned_to", "updated_at"])
        _log(assigned_by, task, "assigned",
             old={"user_id": str(old)} if old else None,
             new={"user_id": str(user.pk)})

        if user.pk != assigned_by.pk:
            from users.services import NotificationService
            NotificationService.create(
                recipient=user,
                notification_type=NotificationType.ASSIGNED,
                message=f"{assigned_by.display_name} assigned you to '{task.title}'",
                actor=assigned_by,
                task_id=task.pk,
                project_id=task.project_id,
            )
        return task

    @staticmethod
    @transaction.atomic
    def add_co_assignee(task: Task, user: User, assigned_by: User) -> TaskAssignment:
        assignment, created = TaskAssignment.objects.get_or_create(
            task=task, user=user, defaults={"assigned_by": assigned_by}
        )
        if created and user.pk != assigned_by.pk:
            from users.services import NotificationService
            NotificationService.create(
                recipient=user,
                notification_type=NotificationType.ASSIGNED,
                message=f"{assigned_by.display_name} added you as co-assignee on '{task.title}'",
                actor=assigned_by,
                task_id=task.pk,
                project_id=task.project_id,
            )
        return assignment

    @staticmethod
    def remove_co_assignee(task: Task, user: User) -> None:
        TaskAssignment.objects.filter(task=task, user=user).delete()

    @staticmethod
    @transaction.atomic
    def soft_delete(task: Task, actor: User) -> Task:
        if task.is_deleted():
            raise ValueError("Task is already deleted.")
        task.deleted_at = timezone.now()
        task.save(update_fields=["deleted_at", "updated_at"])
        _log(actor, task, "deleted")
        return task

    @staticmethod
    @transaction.atomic
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
    @transaction.atomic
    def add_dependency(task: Task, depends_on: Task, dep_type: str, created_by: User) -> TaskDependency:
        if task.pk == depends_on.pk:
            raise ValueError("A task cannot depend on itself.")
        if dep_type not in DependencyType.values:
            raise ValueError(f"Invalid dependency type '{dep_type}'.")
        if _has_dependency_cycle(task, depends_on):
            raise ValueError("CYCLIC_DEPENDENCY")
        return TaskDependency.objects.create(
            task=task, depends_on_task=depends_on, type=dep_type, created_by=created_by
        )

    @staticmethod
    @transaction.atomic
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
        if column.wip_limit is not None:
            current_count = Task.objects.filter(
                board_column=column, deleted_at__isnull=True
            ).exclude(pk=task.pk).count()
            if current_count >= column.wip_limit:
                raise ValueError(
                    f"WIP limit of {column.wip_limit} reached for column '{column.name}'."
                )
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
    @transaction.atomic
    def add_comment(
        task: Task, author: User, body: dict, parent_comment: Comment | None = None
    ) -> Comment:
        if task.is_deleted():
            raise ValueError("Cannot comment on a deleted task.")
        comment = Comment.objects.create(
            task=task, author=author, body=body, parent_comment=parent_comment
        )
        _log(author, task, "commented", new={"comment_id": str(comment.pk)})

        from users.services import NotificationService
        NotificationService.create_for_mentions(body, actor=author, task=task)
        NotificationService.notify_watchers(
            task=task,
            notification_type=NotificationType.COMMENTED,
            message=f"{author.display_name} commented on '{task.title}'",
            actor=author,
        )
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
    def can_restore_task(user: User, task: Task) -> bool:
        """PO/PM (or elevated) may restore a soft-deleted task."""
        if user.has_elevated_access():
            return True
        if not task.is_deleted():
            return False
        membership = ProjectMember.objects.filter(project=task.project, user=user).first()
        if not membership:
            return False
        return membership.role in (ProjectRole.PO, ProjectRole.PM)

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

    @staticmethod
    def workspace_member(user, workspace):
        from projects.models import WorkspaceMember
        return WorkspaceMember.objects.filter(workspace=workspace, user=user).first()

    @staticmethod
    def is_workspace_owner(user, workspace) -> bool:
        return workspace.owner_id == user.pk

    @staticmethod
    def is_workspace_admin_or_owner(user, workspace) -> bool:
        from projects.models import WorkspaceRole
        if workspace.owner_id == user.pk:
            return True
        member = AccessControlService.workspace_member(user, workspace)
        return member is not None and member.role in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN)


# ---------------------------------------------------------------------------
# AttachmentService
# ---------------------------------------------------------------------------

class AttachmentService:
    # SVG is intentionally excluded: it can carry inline <script> tags (XSS).
    ALLOWED_MIME_TYPES = {
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "application/pdf",
        "text/plain", "text/csv",
        "application/zip",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

    @staticmethod
    def _detect_mime(file_obj) -> str:
        """Read the first 2 KB for magic-number detection (python-magic preferred)."""
        head = file_obj.read(2048)
        file_obj.seek(0)
        try:
            import magic
            return magic.from_buffer(head, mime=True)
        except ImportError:
            pass
        return ""

    @staticmethod
    @transaction.atomic
    def upload(task: Task, uploaded_file, uploaded_by: User, comment: Comment | None = None) -> Attachment:
        if uploaded_file.size > AttachmentService.MAX_SIZE_BYTES:
            raise ValueError("File exceeds the 50 MB size limit.")

        declared_mime = (uploaded_file.content_type or "application/octet-stream").split(";")[0].strip()

        # Magic-number verification (if python-magic is installed)
        actual_mime = AttachmentService._detect_mime(uploaded_file)
        if actual_mime and actual_mime not in AttachmentService.ALLOWED_MIME_TYPES:
            raise ValueError(f"File content type '{actual_mime}' is not allowed.")
        if actual_mime and actual_mime != declared_mime:
            raise ValueError("File content does not match the declared MIME type.")

        mime_type = actual_mime if actual_mime else declared_mime
        if mime_type not in AttachmentService.ALLOWED_MIME_TYPES:
            raise ValueError(f"File type '{mime_type}' is not allowed.")

        # Use a random UUID as the storage key so task IDs and filenames don't
        # appear in the URL (prevents enumeration and filename injection).
        storage_key = f"attachments/{_uuid.uuid4()}"
        default_storage.save(storage_key, uploaded_file)

        attachment = Attachment.objects.create(
            task=task,
            comment=comment,
            uploaded_by=uploaded_by,
            filename=uploaded_file.name,
            file_size_bytes=uploaded_file.size,
            mime_type=mime_type,
            storage_key=storage_key,
        )
        _log(uploaded_by, task, "added_attachment", new={"filename": uploaded_file.name})
        return attachment

    @staticmethod
    @transaction.atomic
    def delete_attachment(attachment: Attachment, actor: User) -> None:
        storage_key = attachment.storage_key
        task = attachment.task
        filename = attachment.filename
        attachment.delete()
        try:
            default_storage.delete(storage_key)
        except Exception:
            pass
        if task:
            _log(actor, task, "removed_attachment", old={"filename": filename})
