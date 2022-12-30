from django.urls import path

from .views import admin_pull, admin_push, admin_sync

app_name = "release_tracker"

urlpatterns = [
    path("pull/<int:release_id>/", admin_pull, name="admin_pull"),
    path("push/<int:release_id>/", admin_push, name="admin_push"),
    path("sync/<int:release_id>/", admin_sync, name="admin_sync"),
]
