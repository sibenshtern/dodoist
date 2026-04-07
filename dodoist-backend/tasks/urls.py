from django.urls import path

from .views import (
    CommentDetailView,
    CommentReactionView,
    DashboardStatsView,
    MyTasksView,
    TodayTasksView,
    UserActivityView,
    ProjectActivityView,
    ProjectCustomFieldDetailView,
    ProjectCustomFieldListView,
    ProjectTaskListCreateView,
    TaskActivityView,
    TaskAssignmentDetailView,
    TaskAssignmentListView,
    TaskCommentListView,
    TaskCustomFieldValueDetailView,
    TaskCustomFieldValueListView,
    TaskDependencyDetailView,
    TaskDependencyListView,
    TaskDetailView,
    TaskGuestAccessDetailView,
    TaskGuestAccessListView,
    TaskLabelDetailView,
    TaskLabelListView,
    TaskListCreateView,
    TaskSubtaskListView,
    TaskTimeLogListView,
    TimeLogDetailView,
)

urlpatterns = [
    # Dashboard stats
    path("api/dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),

    # Home page endpoints
    path("api/tasks/today/", TodayTasksView.as_view(), name="tasks-today"),
    path("api/tasks/my/", MyTasksView.as_view(), name="tasks-my"),
    path("api/activity/", UserActivityView.as_view(), name="user-activity"),

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

    # Comments
    path("api/tasks/<uuid:pk>/comments/", TaskCommentListView.as_view(), name="task-comment-list"),
    path("api/comments/<uuid:pk>/", CommentDetailView.as_view(), name="comment-detail"),

    # Activity
    path("api/projects/<uuid:pk>/activity/", ProjectActivityView.as_view(), name="project-activity"),
    path("api/tasks/<uuid:pk>/activity/", TaskActivityView.as_view(), name="task-activity"),

    # Custom fields
    path("api/projects/<uuid:pk>/custom-fields/", ProjectCustomFieldListView.as_view(), name="project-custom-field-list"),
    path("api/projects/<uuid:pk>/custom-fields/<uuid:field_id>/", ProjectCustomFieldDetailView.as_view(), name="project-custom-field-detail"),
    path("api/tasks/<uuid:pk>/custom-field-values/", TaskCustomFieldValueListView.as_view(), name="task-custom-field-values"),
    path("api/tasks/<uuid:pk>/custom-field-values/<uuid:field_id>/", TaskCustomFieldValueDetailView.as_view(), name="task-custom-field-value-set"),

    # Reactions
    path("api/comments/<uuid:pk>/reactions/", CommentReactionView.as_view(), name="comment-reactions"),
    path("api/comments/<uuid:pk>/reactions/<str:emoji>/", CommentReactionView.as_view(), name="comment-reaction-delete"),

    # Time logs
    path("api/tasks/<uuid:pk>/time-logs/", TaskTimeLogListView.as_view(), name="task-time-logs"),
    path("api/time-logs/<uuid:pk>/", TimeLogDetailView.as_view(), name="time-log-detail"),
]
