from django.urls import path

from .consumers import ProjectStreamConsumer

websocket_urlpatterns = [
    path("ws/projects/<int:project_id>/", ProjectStreamConsumer.as_asgi()),
]
