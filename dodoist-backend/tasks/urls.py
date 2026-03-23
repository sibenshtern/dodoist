from django.urls import path

from .views import TaskDetailView, TaskListCreateView

urlpatterns = [
    path("api/tasks/", TaskListCreateView.as_view(), name="task-list-create"),
    path("api/tasks/<uuid:pk>/", TaskDetailView.as_view(), name="task-detail"),
]
