from django.urls import path

from .invitations_views import (
    InvitationAcceptView,
    MyInvitationsView,
    WorkspaceInvitationDetailView,
    WorkspaceInvitationListView,
    WorkspaceInviteLinkView,
)
from .views import (
    BoardColumnDetailView,
    BoardColumnListView,
    BoardDetailView,
    ProjectBoardListView,
    LabelDetailView,
    LabelListCreateView,
    ProjectArchiveView,
    ProjectDetailView,
    ProjectListCreateView,
    ProjectMemberDetailView,
    ProjectMemberListView,
    ProjectSprintListView,
    ProjectUnarchiveView,
    SprintCompleteView,
    SprintDetailView,
    SprintStartView,
    SprintTaskView,
    WorkspaceDetailView,
    WorkspaceLeaveView,
    WorkspaceListCreateView,
    WorkspaceMemberDetailView,
    WorkspaceMemberListView,
    WorkspaceRestoreView,
    WorkspaceTransferOwnershipView,
)

urlpatterns = [
    # Workspaces
    path("api/workspaces/", WorkspaceListCreateView.as_view(), name="workspace-list-create"),
    path("api/workspaces/<slug:slug>/", WorkspaceDetailView.as_view(), name="workspace-detail"),
    path("api/workspaces/<slug:slug>/restore/", WorkspaceRestoreView.as_view(), name="workspace-restore"),
    path("api/workspaces/<slug:slug>/transfer/", WorkspaceTransferOwnershipView.as_view(), name="workspace-transfer"),
    path("api/workspaces/<slug:slug>/leave/", WorkspaceLeaveView.as_view(), name="workspace-leave"),
    path("api/workspaces/<slug:slug>/members/", WorkspaceMemberListView.as_view(), name="workspace-member-list"),
    path("api/workspaces/<slug:slug>/members/<uuid:user_id>/", WorkspaceMemberDetailView.as_view(), name="workspace-member-detail"),

    # Workspace invitations
    path("api/workspaces/<slug:slug>/invitations/", WorkspaceInvitationListView.as_view(), name="workspace-invitation-list"),
    path("api/workspaces/<slug:slug>/invitations/<uuid:invite_id>/", WorkspaceInvitationDetailView.as_view(), name="workspace-invitation-detail"),
    path("api/workspaces/<slug:slug>/invite-links/", WorkspaceInviteLinkView.as_view(), name="workspace-invite-link"),

    # Global invitation endpoints
    path("api/invitations/accept/", InvitationAcceptView.as_view(), name="invitation-accept"),
    path("api/invitations/me/", MyInvitationsView.as_view(), name="my-invitations"),

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

    # Sprints
    path("api/projects/<uuid:pk>/sprints/", ProjectSprintListView.as_view(), name="project-sprint-list"),
    path("api/sprints/<uuid:pk>/", SprintDetailView.as_view(), name="sprint-detail"),
    path("api/sprints/<uuid:pk>/start/", SprintStartView.as_view(), name="sprint-start"),
    path("api/sprints/<uuid:pk>/complete/", SprintCompleteView.as_view(), name="sprint-complete"),
    path("api/sprints/<uuid:pk>/tasks/", SprintTaskView.as_view(), name="sprint-task-add"),
    path("api/sprints/<uuid:pk>/tasks/<uuid:task_id>/", SprintTaskView.as_view(), name="sprint-task-remove"),

    # Boards
    path("api/projects/<uuid:pk>/boards/", ProjectBoardListView.as_view(), name="project-board-list"),
    path("api/boards/<uuid:pk>/", BoardDetailView.as_view(), name="board-detail"),
    path("api/boards/<uuid:pk>/columns/", BoardColumnListView.as_view(), name="board-column-list"),
    path("api/boards/<uuid:board_pk>/columns/<uuid:pk>/", BoardColumnDetailView.as_view(), name="board-column-detail"),
]
