"""Ponte síncrono → channel layer · sync → channel layer bridge (usada pelas tarefas · by tasks)."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from .consumers import user_group


def notify_user(user_id: int, event: str, **data) -> None:
    """Envia `{"event": …, "at": …, **data}` a todas as ligações do utilizador.
    Sends `{"event": …, "at": …, **data}` to every connection of that user."""
    layer = get_channel_layer()
    payload = {"event": event, "at": timezone.now().isoformat(), **data}
    async_to_sync(layer.group_send)(user_group(user_id), {"type": "notify", "payload": payload})
