"""Ficha 05, parte 3 — WebSocket: handshake JWT, grupo por utilizador, group_send.
Ficha 05, part 3 — WebSocket: JWT handshake, per-user group, group_send."""

# transaction=True: o consumer corre noutra thread/ligação e tem de ver os dados (commit real).
# Custo: no fim de cada teste há um flush — os dados das migrações (o grupo `gestores`) vão-se,
# por isso o conftest usa get_or_create.
# transaction=True: the consumer runs on another thread/connection and must see committed data.
# Cost: each test ends with a flush — migration data (the `gestores` group) is gone, hence the
# get_or_create in conftest.

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken

from accounts.factories import UserFactory
from config.asgi import application
from shop.notify import notify_user


async def connect(token: str | None):
    qs = f"?token={token}" if token else ""
    communicator = WebsocketCommunicator(application, f"/ws/notifications/{qs}")
    communicator.scope["headers"] = [
        (b"origin", b"http://localhost")
    ]  # AllowedHostsOriginValidator
    connected, code = await communicator.connect()
    return communicator, connected, code


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_anonymous_websocket_is_closed_with_4401():
    communicator, connected, _ = await connect(None)
    assert connected  # aceite, e logo fechada com um código que o browser consegue ler
    assert (await communicator.receive_output())["code"] == 4401
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_invalid_token_is_closed_with_4401():
    communicator, connected, _ = await connect("not-a-jwt")
    assert connected
    assert (await communicator.receive_output())["code"] == 4401
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_user_receives_only_their_own_notifications():
    ana = await database_sync_to_async(UserFactory)(username="ana")
    bruno = await database_sync_to_async(UserFactory)(username="bruno")
    ws_ana, connected, _ = await connect(str(AccessToken.for_user(ana)))
    assert connected
    assert (await ws_ana.receive_json_from())["event"] == "connected"

    await database_sync_to_async(notify_user)(bruno.id, "order.paid", order_id=7)  # para o Bruno
    await database_sync_to_async(notify_user)(ana.id, "report.ready", task_id="abc")  # para a Ana
    message = await ws_ana.receive_json_from()
    assert message["event"] == "report.ready" and message["task_id"] == "abc"
    assert await ws_ana.receive_nothing()  # o aviso do Bruno nunca chegou aqui · Bruno's never came

    await ws_ana.send_json_to({"type": "ping"})
    assert (await ws_ana.receive_json_from())["event"] == "pong"
    await ws_ana.disconnect()
