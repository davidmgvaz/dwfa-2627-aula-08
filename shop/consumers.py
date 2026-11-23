"""O servidor fala primeiro · the server speaks first (Ficha 05, Aula 07).

PT: um consumer por ligação; cada utilizador autenticado entra no grupo `user_<id>`.
Quem quer avisá-lo (uma tarefa Celery, uma view) faz `group_send` para esse grupo —
não precisa de saber quantos separadores tem abertos.
EN: one consumer per connection; every authenticated user joins group `user_<id>`.
Whoever wants to reach them (a Celery task, a view) does `group_send` to that group —
without knowing how many tabs they have open.
"""

from channels.generic.websocket import AsyncJsonWebsocketConsumer


def user_group(user_id: int) -> str:
    return f"user_{user_id}"


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            # Aceitar primeiro: um close antes do accept é um handshake recusado (HTTP 403) e o
            # browser só vê o código 1006. 4xxx = códigos de aplicação; 4401 ≈ 401.
            # Accept first: closing before accept is a rejected handshake (HTTP 403) and the
            # browser only sees code 1006. 4xxx are application codes; 4401 ≈ 401.
            await self.accept()
            await self.close(code=4401)
            return
        self.group = user_group(user.id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self.send_json({"event": "connected", "user": user.get_username()})

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # O cliente só manda pings; tudo o resto é ignorado · the client only pings
        if content.get("type") == "ping":
            await self.send_json({"event": "pong"})

    async def notify(self, event):
        # chega por group_send({"type": "notify", "payload": {...}}) · arrives via group_send
        await self.send_json(event["payload"])
