from django.urls import path

from .consumers import ProjectStreamConsumer

websocket_urlpatterns = [
    # Channels routes ASGI apps through Django's path(); the stubs only know views.
    path("ws/projects/<int:project_id>/", ProjectStreamConsumer.as_asgi()),  # pyright: ignore[reportCallIssue, reportArgumentType]
]
