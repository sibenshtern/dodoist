from django.urls import path

from .views import WorkspaceDetailView, WorkspaceListCreateView, WorkspaceMemberDetailView, WorkspaceMemberListView

urlpatterns = [
    path("api/workspaces/", WorkspaceListCreateView.as_view(), name="workspace-list-create"),
    path("api/workspaces/<slug:slug>/", WorkspaceDetailView.as_view(), name="workspace-detail"),
    path("api/workspaces/<slug:slug>/members/", WorkspaceMemberListView.as_view(), name="workspace-member-list"),
    path("api/workspaces/<slug:slug>/members/<uuid:user_id>/", WorkspaceMemberDetailView.as_view(), name="workspace-member-detail"),
]
