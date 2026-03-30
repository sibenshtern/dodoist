from django.urls import path

from .views import (
    ProjectTaskListCreateView,
    TaskAssignmentDetailView,
    TaskAssignmentListView,
    TaskDependencyDetailView,
    TaskDependencyListView,
    TaskDetailView,
    TaskGuestAccessDetailView,
    TaskGuestAccessListView,
    TaskLabelDetailView,
    TaskLabelListView,
    TaskListCreateView,
    TaskSubtaskListView,
)

urlpatterns = [
    # Project-nested task list/create (spec-compliant)
    path("api/projects/<uuid:pk>/tasks/", ProjectTaskListCreateView.as_view(), name="project-task-list-create"),

    # Legacy flat task endpoints
    path("api/tasks/", TaskListCreateView.as_view(), name="task-list-create"),
    path("api/tasks/<uuid:pk>/", TaskDetailView.as_view(), name="task-detail"),

    # Subtasks
    path("api/tasks/<uuid:pk>/subtasks/", TaskSubtaskListView.as_view(), name="task-subtask-list"),

    # Co-assignees
    path("api/tasks/<uuid:pk>/assignments/", TaskAssignmentListView.as_view(), name="task-assignment-list"),
    path("api/tasks/<uuid:pk>/assignments/<uuid:user_id>/", TaskAssignmentDetailView.as_view(), name="task-assignment-detail"),

    # Labels
    path("api/tasks/<uuid:pk>/labels/", TaskLabelListView.as_view(), name="task-label-list"),
    path("api/tasks/<uuid:pk>/labels/<uuid:label_id>/", TaskLabelDetailView.as_view(), name="task-label-detail"),

    # Dependencies
    path("api/tasks/<uuid:pk>/dependencies/", TaskDependencyListView.as_view(), name="task-dependency-list"),
    path("api/tasks/<uuid:pk>/dependencies/<uuid:dep_id>/", TaskDependencyDetailView.as_view(), name="task-dependency-detail"),

    # Guest access
    path("api/tasks/<uuid:pk>/guest-access/", TaskGuestAccessListView.as_view(), name="task-guest-access-list"),
    path("api/tasks/<uuid:pk>/guest-access/<uuid:user_id>/", TaskGuestAccessDetailView.as_view(), name="task-guest-access-detail"),
]
