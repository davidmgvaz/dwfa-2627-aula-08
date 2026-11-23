"""Settings partilhados por todos os ambientes · settings shared by every environment.

PT: tudo o que é igual em dev, test e prod vive aqui; o que muda vem do ambiente
(`.env`, nunca no git). EN: everything identical across dev, test and prod lives
here; whatever differs comes from the environment (`.env`, never in git).
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "daphne",  # Ficha 05: `runserver` passa a servir ASGI (HTTP + WebSocket) · ASGI runserver
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # terceiros · third party (Ficha 02)
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
    "channels",  # Ficha 05
    # apps do projeto · project apps
    "accounts",
    "core",
    "shop",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # primeiro: o preflight não traz Authorization
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {"default": env.db("DATABASE_URL")}

# Modelo de utilizador próprio desde o primeiro dia · custom user model from day one
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Lisbon"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework — fechado por omissão desde a Ficha 03 · closed by default since Ficha 03
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",  # Authorization: Bearer
        "rest_framework.authentication.SessionAuthentication",  # admin + Browsable API
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_THROTTLE_RATES": {"anon": "100/hour", "user": "1000/hour", "auth": "10/minute"},
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "EXCEPTION_HANDLER": "shop.api.problem_details_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "ISLA DWFA e-commerce API",
    "DESCRIPTION": "Ficha 02 — domínio e-commerce exposto com Django REST Framework",
    "VERSION": "0.4.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # Ficha 04 (Aula 06): um componente para o pedido (`ProductRequest`, sem os read_only)
    # e outro para a resposta (`Product`, com tudo) — sem isto os tipos gerados do OpenAPI
    # exigem `access`/`refresh` no corpo do login e marcam `stock` opcional na resposta.
    # One component for the request (`ProductRequest`, no read_only fields) and one for the
    # response (`Product`, everything) — without it the generated TS types are unusable.
    "COMPONENT_SPLIT_REQUEST": True,
}

# JWT (Ficha 03) · tempos de vida em docs/decisions.md · lifetimes in docs/decisions.md
from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

# CORS (Ficha 03) — lista explícita, por ambiente · explicit allowlist, per environment
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:5173"])
CORS_URLS_REGEX = r"^/api/.*$"

# Passwords (Ficha 03) — Argon2 primeiro, PBKDF2 mantém os hashes antigos válidos
# Argon2 first; PBKDF2 keeps existing hashes valid (re-hashed on next login)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS[1]["OPTIONS"] = {"min_length": 12}

# Segredos: rotação sem logout geral · key rotation without logging everyone out
SECRET_KEY_FALLBACKS = env.list("SECRET_KEY_FALLBACKS", default=[])

# ---------------------------------------------------------------------------------------
# Ficha 05 (Aula 07) — um Redis, três usos, três bases · one Redis, three uses, three DBs
#   /0 fila do Celery (broker + resultados) · /1 cache do Django · /2 channel layer
# ---------------------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379")

# Celery — prefixo CELERY_ lido por config/celery.py · read by config/celery.py
CELERY_BROKER_URL = f"{REDIS_URL}/0"
CELERY_RESULT_BACKEND = f"{REDIS_URL}/0"
CELERY_RESULT_EXPIRES = 60 * 60  # 1 h: o cliente pergunta pelo estado dentro desta janela
CELERY_TASK_ACKS_LATE = True  # ack no fim: um worker que morre a meio devolve a mensagem à fila
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # com acks_late, um pedido de cada vez · one at a time
CELERY_TASK_SOFT_TIME_LIMIT = 60  # SoftTimeLimitExceeded na tarefa · raised inside the task
CELERY_TASK_TIME_LIMIT = 120  # o worker mata a tarefa · the worker kills the task
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_TIMEZONE = TIME_ZONE

# Channels — grupos por utilizador através do Redis · per-user groups through Redis
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [f"{REDIS_URL}/2"]},
    }
}

# Cache — respostas do catálogo, versões, "quem é o dono desta tarefa"
# Cache — catalogue responses, version keys, "who owns this task"
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"{REDIS_URL}/1",
        "TIMEOUT": 300,
        "KEY_PREFIX": "shop",
    }
}

# Botões da demo · demo knobs (ver tasks.py)
RECEIPT_FLAKY = env.bool("RECEIPT_FLAKY", default=False)  # 1.ª tentativa falha → retry
REPORT_STEP_SECONDS = env.float("REPORT_STEP_SECONDS", default=0.2)  # progresso visível
