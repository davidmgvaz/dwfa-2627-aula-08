"""Autenticação JWT para WebSockets · JWT authentication for WebSockets (Ficha 05).

PT: o browser não pode pôr `Authorization: Bearer` num `new WebSocket(url)`; o token
vai na query string (`?token=`) e é validado UMA vez, no handshake. Depois disso a
ligação é do utilizador — mesmo que o access expire (30 min), a ligação fica aberta.
EN: the browser cannot set `Authorization: Bearer` on `new WebSocket(url)`; the token
travels in the query string and is validated ONCE, at the handshake. From then on the
connection belongs to the user — it stays open even after the access token expires.
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken, TokenError


@database_sync_to_async
def user_from_token(raw_token: str | None):
    if not raw_token:
        return AnonymousUser()
    auth = JWTAuthentication()
    try:
        validated = auth.get_validated_token(raw_token)  # assinatura + expiração · signature + exp
        return auth.get_user(validated)  # existe e is_active · exists and is_active
    except (InvalidToken, TokenError, AuthenticationFailed):
        return AnonymousUser()


class JWTAuthMiddleware:
    """Põe `scope["user"]` a partir de `?token=<access>` · sets `scope["user"]` from `?token=`."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        scope["user"] = await user_from_token(query.get("token", [None])[0])
        return await self.inner(scope, receive, send)
