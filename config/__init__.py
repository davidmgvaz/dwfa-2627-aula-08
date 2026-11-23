# Garante que o `app` Celery é carregado com o Django, para que `@shared_task` use a sua
# configuração.
# Makes sure the Celery `app` loads with Django, so `@shared_task` picks up its configuration.
from .celery import app as celery_app

__all__ = ("celery_app",)
