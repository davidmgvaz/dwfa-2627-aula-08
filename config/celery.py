"""A aplicação Celery · the Celery app (Ficha 05, Aula 07).

PT: um só objeto `app`; a configuração vem dos settings do Django (prefixo `CELERY_`),
as tarefas são descobertas em `<app>/tasks.py`. O worker arranca com
`uv run celery -A config worker -l info`.
EN: one `app` object; configuration comes from Django settings (`CELERY_` prefix),
tasks are discovered in `<app>/tasks.py`. Start the worker with
`uv run celery -A config worker -l info`.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
