from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from organizations.permissions import user_can_access_project


def project_group_name(project_id: int) -> str:
    return f"project.{project_id}"


class ProjectStreamConsumer(AsyncJsonWebsocketConsumer):
    """Streams `issue.created` / `issue.updated` messages for one project."""

    group_name: str | None = None

    async def connect(self) -> None:
        user = self.scope.get("user")
        project_id = int(self.scope["url_route"]["kwargs"]["project_id"])
        allowed = bool(user and user.is_authenticated) and await database_sync_to_async(
            user_can_access_project
        )(user, project_id)
        if not allowed:
            await self.close(code=4403)
            return
        self.group_name = project_group_name(project_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def issue_update(self, message: dict[str, Any]) -> None:
        await self.send_json(message["payload"])
