"""Testes (pytest-django) · tests."""

from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ["localhost", "testserver"]  # Origin dos WebSockets de teste · test WS origin

# Hasher rápido: os testes não medem a força das passwords · fast hasher: tests do not
# benchmark password strength
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Ficha 05 — sem Redis nos testes: tudo em memória, no processo do pytest
# Ficha 05 — no Redis in tests: everything in memory, inside the pytest process
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
CELERY_TASK_ALWAYS_EAGER = True  # `.delay()` corre já, aqui · runs right away, in-process
CELERY_TASK_EAGER_PROPAGATES = True  # exceções da tarefa chegam ao teste · exceptions surface
CELERY_TASK_STORE_EAGER_RESULT = True  # AsyncResult(id) vê o resultado · result is readable
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
RECEIPT_FLAKY = False
REPORT_STEP_SECONDS = 0
