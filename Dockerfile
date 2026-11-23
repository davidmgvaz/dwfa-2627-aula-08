# syntax=docker/dockerfile:1
# Imagem do backend · backend image (Aula 08) — a mesma para a API e para o worker
# One image for the API and for the Celery worker: same code, another command.

# ---- 1 · build: só as dependências, numa venv · dependencies only, into a venv ----
FROM python:3.13-slim AS build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
# primeiro o que muda pouco: esta camada fica em cache enquanto o uv.lock não mudar
# what changes rarely goes first: this layer stays cached until uv.lock changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ---- 2 · runtime: sem uv, sem compiladores, sem root · no uv, no compilers, no root ----
FROM python:3.13-slim
RUN useradd --create-home app
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod
COPY --from=build /app/.venv .venv
COPY . .
# os valores abaixo só existem durante o build · these values exist only at build time
RUN SECRET_KEY=build DATABASE_URL=postgres://build ALLOWED_HOSTS=build \
    python manage.py collectstatic --noinput
USER app
EXPOSE 8000
# ASGI (HTTP + WebSocket) com workers Uvicorn geridos pelo Gunicorn.
# Sem Channels: `gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2`
CMD ["gunicorn", "config.asgi:application", "-k", "uvicorn_worker.UvicornWorker", \
     "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-"]
