from django.contrib import admin

from .models import (
    Board,
    BoardColumn,
    Label,
    Project,
    ProjectMember,
    Sprint,
    Workspace,
    WorkspaceMember,
)


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "plan", "is_personal", "created_at")
    list_filter = ("plan", "is_personal")
    search_fields = ("name", "slug", "owner__email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(WorkspaceMember)
class WorkspaceMemberAdmin(admin.ModelAdmin):
    list_display = ("workspace", "user", "joined_at")
    search_fields = ("workspace__name", "user__email")
    ordering = ("-joined_at",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "workspace", "type", "status", "is_private", "created_at")
    list_filter = ("type", "status", "is_private")
    search_fields = ("name", "key", "workspace__name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "archived_at")


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "role", "joined_at")
    list_filter = ("role",)
    search_fields = ("project__name", "user__email")
    ordering = ("-joined_at",)


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ("name", "color", "workspace", "created_by", "created_at")
    search_fields = ("name", "workspace__name")
    ordering = ("name",)
    readonly_fields = ("created_at",)


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "status", "start_date", "end_date")
    list_filter = ("status",)
    search_fields = ("name", "project__name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "completed_at")


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "type", "is_default", "created_at")
    list_filter = ("type", "is_default")
    search_fields = ("name", "project__name")
    ordering = ("-created_at",)


@admin.register(BoardColumn)
class BoardColumnAdmin(admin.ModelAdmin):
    list_display = ("name", "board", "status_mapping", "position", "wip_limit")
    list_filter = ("status_mapping",)
    search_fields = ("name", "board__name")
    ordering = ("board", "position")
