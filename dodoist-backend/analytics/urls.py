from django.urls import path

from .views import (
    ProjectMemberMetricsView,
    ProjectMetricsSummaryView,
    ProjectSnapshotListView,
    UserMetricsView,
)

urlpatterns = [
    path("api/projects/<uuid:pk>/snapshots/", ProjectSnapshotListView.as_view(), name="project-snapshots"),
    path("api/projects/<uuid:pk>/metrics/summary/", ProjectMetricsSummaryView.as_view(), name="project-metrics-summary"),
    path("api/projects/<uuid:pk>/metrics/users/", ProjectMemberMetricsView.as_view(), name="project-metrics-users"),
    path("api/users/<uuid:pk>/metrics/", UserMetricsView.as_view(), name="user-metrics"),
]
