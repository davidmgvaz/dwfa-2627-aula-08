"""Cache do catálogo com invalidação por versão · catalogue cache with version-key invalidation.

PT: em vez de apagar chaves (o Redis não lista chaves de graça), guardamos um número de
versão; cada chave de cache inclui-o; invalidar = incrementar. As chaves antigas morrem
sozinhas pelo TTL.
EN: instead of deleting keys (listing keys in Redis is not free), we keep a version number
that every cache key embeds; invalidating = incrementing it. Old keys expire on their own.
"""

from django.core.cache import cache

VERSION_KEY = "catalogue:version"


def catalogue_version() -> int:
    return cache.get_or_set(VERSION_KEY, 1, timeout=None)


def bump_catalogue_version() -> None:
    try:
        cache.incr(VERSION_KEY)
    except ValueError:  # a chave ainda não existe · key does not exist yet
        cache.set(VERSION_KEY, 2, timeout=None)
