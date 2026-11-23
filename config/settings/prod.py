"""Produção · production (Aula 08: deploy)."""

from .base import *  # noqa: F403
from .base import MIDDLEWARE, env

DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# HTTPS — ligado por omissão; só o «prod» local em http://localhost o desliga, no .env
# HTTPS — on by default; only the local "prod" on http://localhost switches it off, in .env
HTTPS = env.bool("HTTPS", default=True)
SECURE_SSL_REDIRECT = HTTPS
SESSION_COOKIE_SECURE = HTTPS
CSRF_COOKIE_SECURE = HTTPS
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365 if HTTPS else 0  # 1 ano · 1 year (preload list)
SECURE_HSTS_INCLUDE_SUBDOMAINS = HTTPS
SECURE_HSTS_PRELOAD = HTTPS  # Ficha 03: check --deploy W021
# O Nginx termina o TLS e diz-nos o esquema original · Nginx terminates TLS and tells us
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# O health check fala HTTP simples dentro da rede dos contentores: sem redirect
# The health check speaks plain HTTP inside the container network: no redirect
SECURE_REDIRECT_EXEMPT = [r"^api/health/$"]

# Estáticos (admin, Swagger) servidos pelo próprio processo, comprimidos e com hash no nome
# Static files (admin, Swagger) served by the app process, compressed and hashed
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Email: SMTP por omissão; o «prod» local escreve para o log do worker
# Email: SMTP by default; the local "prod" writes to the worker log
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
