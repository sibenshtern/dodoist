from django.contrib import admin

from .models import (
    ActivityLog,
    Comment,
    CustomField,
    Reaction,
    Task,
    TaskAssignment,
    TaskCustomFieldValue,
    TaskDependency,
    TaskGuestAccess,
    TaskLabel,
    TimeLog,
)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "status", "priority", "project", "assigned_to", "due_date", "created_at")
    list_filter = ("type", "status", "priority")
    search_fields = ("title", "project__name", "assigned_to__email", "created_by__email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "completed_at", "deleted_at")
    raw_id_fields = ("project", "assigned_to", "created_by", "sprint", "board_column", "parent_task")


@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = ("task", "user", "assigned_by", "assigned_at")
    search_fields = ("task__title", "user__email")
    ordering = ("-assigned_at",)


@admin.register(TaskLabel)
class TaskLabelAdmin(admin.ModelAdmin):
    list_display = ("task", "label")
    search_fields = ("task__title", "label__name")


@admin.register(TaskDependency)
class TaskDependencyAdmin(admin.ModelAdmin):
    list_display = ("task", "type", "depends_on_task", "created_by", "created_at")
    list_filter = ("type",)
    search_fields = ("task__title",)
    readonly_fields = ("created_at",)


@admin.register(TaskGuestAccess)
class TaskGuestAccessAdmin(admin.ModelAdmin):
    list_display = ("task", "user", "granted_by", "granted_at", "expires_at")
    search_fields = ("task__title", "user__email")
    readonly_fields = ("granted_at",)


@admin.register(CustomField)
class CustomFieldAdmin(admin.ModelAdmin):
    list_display = ("name", "field_type", "project", "is_required", "position", "created_at")
    list_filter = ("field_type", "is_required")
    search_fields = ("name", "project__name")
    readonly_fields = ("created_at",)


@admin.register(TaskCustomFieldValue)
class TaskCustomFieldValueAdmin(admin.ModelAdmin):
    list_display = ("task", "custom_field", "value", "updated_at")
    search_fields = ("task__title", "custom_field__name")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("task", "author", "is_edited", "created_at")
    list_filter = ("is_edited",)
    search_fields = ("task__title", "author__email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "deleted_at")


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ("comment", "user", "emoji", "created_at")
    search_fields = ("user__email",)
    readonly_fields = ("created_at",)


@admin.register(TimeLog)
class TimeLogAdmin(admin.ModelAdmin):
    list_display = ("task", "user", "logged_minutes", "logged_date", "created_at")
    search_fields = ("task__title", "user__email")
    ordering = ("-logged_date",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("action", "entity_type", "actor", "project", "created_at")
    list_filter = ("entity_type", "action")
    search_fields = ("actor__email", "action")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
