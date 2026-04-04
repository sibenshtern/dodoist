from django.urls import include, path

urlpatterns = [
    path("", include("users.urls")),
    path("", include("tasks.urls")),
    path("", include("projects.urls")),
]
