"""ASGI — HTTP continua no Django; WebSocket vai para o Channels · HTTP stays with Django;
WebSocket goes to Channels (Ficha 05, Aula 07)."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

# Primeiro o Django (carrega as apps); só depois importar o que toca nos modelos.
# Django first (loads the apps); only then import anything that touches models.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

from accounts.ws_auth import JWTAuthMiddleware  # noqa: E402
from shop.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        # Origin ∈ ALLOWED_HOSTS → token JWT na query string → consumer
        # Origin ∈ ALLOWED_HOSTS → JWT in the query string → consumer
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddleware(URLRouter(websocket_urlpatterns))
        ),
    }
)
