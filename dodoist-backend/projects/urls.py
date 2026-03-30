from django.urls import path

from .views import (
    LabelDetailView,
    LabelListCreateView,
    ProjectArchiveView,
    ProjectDetailView,
    ProjectListCreateView,
    ProjectMemberDetailView,
    ProjectMemberListView,
    ProjectUnarchiveView,
    WorkspaceDetailView,
    WorkspaceListCreateView,
    WorkspaceMemberDetailView,
    WorkspaceMemberListView,
)

urlpatterns = [
    # Workspaces
    path("api/workspaces/", WorkspaceListCreateView.as_view(), name="workspace-list-create"),
    path("api/workspaces/<slug:slug>/", WorkspaceDetailView.as_view(), name="workspace-detail"),
    path("api/workspaces/<slug:slug>/members/", WorkspaceMemberListView.as_view(), name="workspace-member-list"),
    path("api/workspaces/<slug:slug>/members/<uuid:user_id>/", WorkspaceMemberDetailView.as_view(), name="workspace-member-detail"),

    # Projects (nested under workspace for creation/listing)
    path("api/workspaces/<slug:slug>/projects/", ProjectListCreateView.as_view(), name="project-list-create"),

    # Projects (direct access by UUID)
    path("api/projects/<uuid:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path("api/projects/<uuid:pk>/archive/", ProjectArchiveView.as_view(), name="project-archive"),
    path("api/projects/<uuid:pk>/unarchive/", ProjectUnarchiveView.as_view(), name="project-unarchive"),

    # Project members
    path("api/projects/<uuid:pk>/members/", ProjectMemberListView.as_view(), name="project-member-list"),
    path("api/projects/<uuid:pk>/members/<uuid:user_id>/", ProjectMemberDetailView.as_view(), name="project-member-detail"),

    # Labels (nested under workspace)
    path("api/workspaces/<slug:slug>/labels/", LabelListCreateView.as_view(), name="label-list-create"),
    path("api/workspaces/<slug:slug>/labels/<uuid:label_id>/", LabelDetailView.as_view(), name="label-detail"),
]
