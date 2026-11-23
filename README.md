# Aula 08 — Qualidade e entrega: CI, Docker, Nginx · Quality and delivery: CI, Docker, Nginx

[![CI](https://github.com/davidmgvaz/dwfa-2627-aula-08/actions/workflows/ci.yml/badge.svg)](https://github.com/davidmgvaz/dwfa-2627-aula-08/actions/workflows/ci.yml)

**Desenvolvimento Web Full-stack Avançado** · Mestrado em Engenharia Informática · ISLA Gaia · 2026/27 · David Vaz

> **PT** — Este repositório é a pasta [`aula-08/`](https://github.com/davidmgvaz/dwfa-2627-solucoes/tree/main/aula-08) de `dwfa-2627-solucoes` posta na **raiz de um repositório próprio**, para o *workflow* de CI correr de facto: o GitHub só executa o que está em `.github/workflows/` na raiz. Vejam o separador **Actions** (três *jobs*: `backend`, `frontend`, `images`), o selo acima e os *pull requests*, onde as verificações aparecem lado a lado. É o que os pontos 7 e 8 do M2 pedem no repositório do vosso grupo.
> **EN** — This repository is the `aula-08/` folder of `dwfa-2627-solucoes` placed at the **root of its own repository**, so that the CI workflow actually runs: GitHub only executes what is in `.github/workflows/` at the root. Look at the **Actions** tab (three jobs: `backend`, `frontend`, `images`), the badge above and the pull requests, where the checks show side by side. This is what M2 points 7 and 8 ask for in your group's repository.


Aula 08 (23/11/2026) · referência para o ponto 7 (CI) e o ponto 8 (contentores) do M2 · reference for M2 points 7 (CI) and 8 (containers) — construída sobre `ficha-05/` · built on top of `ficha-05/`. O código da aplicação não muda; o que é novo é **como se verifica e como se entrega** · the application code does not change; what is new is **how it is checked and how it is shipped**.

**PT** — Um `Dockerfile` *multi-stage* para o backend (uv no build; Gunicorn com *workers* Uvicorn no runtime, sem root), a mesma imagem para a API e para o *worker* Celery; um `frontend/Dockerfile` que constrói a SPA com Node e a serve com Nginx (`try_files` para o `index.html`; `/api/`, `/admin/`, `/static/` e `/ws/` encaminhados para o backend); um `compose.prod.yaml` com cinco serviços e uma só porta publicada; e um *workflow* de CI com três *jobs* (backend, frontend, imagens). Não é a única resposta certa: comparem com o vosso repositório.
**EN** — A multi-stage backend `Dockerfile` (uv at build time; Gunicorn with Uvicorn workers at runtime, non-root), one image for the API and the Celery worker; a `frontend/Dockerfile` that builds the SPA with Node and serves it with Nginx; a `compose.prod.yaml` with five services and a single published port; and a CI workflow with three jobs (backend, frontend, images). Not the only correct answer: compare it with your own repository.

## Onde ver o CI · Where to see the CI

- **Actions** → cada *push* e cada *pull request* corre `backend`, `frontend` (em paralelo) e depois `images` · every push and pull request runs `backend` and `frontend` in parallel, then `images`.
- **Pull requests** → o [#1](https://github.com/davidmgvaz/dwfa-2627-aula-08/pull/1) está verde; o [#2](https://github.com/davidmgvaz/dwfa-2627-aula-08/pull/2) está **vermelho de propósito**: a versão da API mudou e o `schema.yaml` não foi regenerado, e a verificação de desvio apanha-o · #1 is green; #2 is **red on purpose**: the API version changed and `schema.yaml` was not regenerated, and the drift check catches it.
- O ficheiro é [`.github/workflows/ci.yml`](.github/workflows/ci.yml) · the file is `.github/workflows/ci.yml`.

```sh
cp env.example .env                  # e editar · and edit: SECRET_KEY, POSTGRES_PASSWORD
docker compose -f compose.prod.yaml up --build -d
docker compose -f compose.prod.yaml exec web python manage.py migrate
docker compose -f compose.prod.yaml exec web python manage.py seed
# → http://localhost   (ana / pass1234)
docker compose -f compose.prod.yaml up -d --scale web=2      # duas réplicas · two replicas
curl -si localhost/api/health/ | grep -i x-upstream          # repetir: os endereços alternam · repeat: addresses alternate
docker compose -f compose.prod.yaml down                     # -v apaga também os dados · -v also deletes the data
```

> **Nota · Note** — nesta pasta o ficheiro de exemplo chama-se **`env.example`** (sem ponto), na raiz e em `frontend/`; nas fichas anteriores era `.env.example`. O conteúdo e o uso são os mesmos: `cp env.example .env`. No vosso projeto mantenham o nome `.env.example`, que é o que a checklist do M2 pede. · In this folder the example file is called **`env.example`** (no leading dot), at the root and in `frontend/`; earlier fichas used `.env.example`. Same content, same use. In your own project keep `.env.example`, which is what the M2 checklist asks for.

Variáveis do `.env` para o «prod» local · `.env` variables for the local "prod":

```sh
SECRET_KEY=            # python -c "import secrets; print(secrets.token_urlsafe(50))"
POSTGRES_PASSWORD=     # qualquer valor, só vive no volume local · any value, local volume only
HTTPS=false            # http://localhost não tem TLS; em produção fica true (o valor por omissão)
ALLOWED_HOSTS=localhost
HTTP_PORT=80           # 8080 se a porta 80 estiver ocupada · if port 80 is busy
```

## O que é novo · What is new

`Dockerfile` · `.dockerignore` · `frontend/Dockerfile` · `frontend/.dockerignore` · `frontend/nginx.conf` · `frontend/.npmrc` · `compose.prod.yaml` · `.github/workflows/ci.yml` (três *jobs* · three jobs) · `config/settings/prod.py` (`HTTPS`, WhiteNoise, `SECURE_REDIRECT_EXEMPT` para o *health check*, `EMAIL_BACKEND`) · `pyproject.toml` (`gunicorn`, `uvicorn-worker`, `websockets`, `whitenoise`; `factory-boy` passa a dependência normal) · `frontend/package.json` (`gen:api`) · `frontend/src/api/schema.d.ts` regenerado · regenerated.

## O que se verifica · What to check

1. Num clone limpo, os quatro comandos acima e `http://localhost` mostra o catálogo; login com `ana` · on a clean clone the four commands above and the catalogue shows; log in as `ana`.
2. `http://localhost/orders` sem sessão leva ao login e volta; F5 em `/orders` não dá 404 (`try_files`) · the guard works and a reload on a client route is not a 404.
3. `docker compose -f compose.prod.yaml ps` → `db`, `redis` e `web` *healthy*; só o `nginx` publica uma porta · only `nginx` publishes a port.
4. Pagar uma encomenda → `docker compose -f compose.prod.yaml logs worker` mostra o recibo · pay an order and the worker log shows the receipt.
5. `--scale web=2` e `curl` repetido → `X-Upstream` alterna entre dois endereços · two upstream addresses alternate.
6. `new WebSocket('ws://localhost/ws/notifications/?token=<access>')` → `{"event":"connected"}` através do Nginx · the WebSocket works through Nginx.
7. `docker compose -f compose.prod.yaml exec web python manage.py check --deploy` limpo com `HTTPS=true` · clean with `HTTPS=true`.
8. CI: `uv run pytest` (51) · `ruff` · `makemigrations --check` · `schema.yaml` igual ao gerado · `npm ci` · `gen:api` sem diferenças · `type-check` · `oxlint`/`eslint` · `test:unit -- --run` (10) · `build-only` · as imagens constroem · the images build.

## Erros comuns · Common mistakes

- `npm ci` falha com `ERESOLVE` (openapi-typescript 7 pede TypeScript 5, o create-vue instala o 6) → `frontend/.npmrc` com `legacy-peer-deps=true`, **copiado para a imagem antes do `npm ci`** · commit an `.npmrc` and copy it before `npm ci`.
- `manage.py seed` na imagem → `ModuleNotFoundError: factory` porque o `factory-boy` era dependência de desenvolvimento · the seed needs `factory-boy` as a regular dependency.
- `COPY . .` antes de instalar as dependências → cada alteração ao código reinstala tudo · copy the lockfile first, the code last.
- Sem `.dockerignore` → o `.env` e a `.venv` vão para dentro da imagem · secrets and the local venv end up in the image.
- `runserver` no `CMD` · `DEBUG=True` em produção → nunca · never.
- `VITE_API_URL=http://localhost:8000` na imagem do *frontend* → a SPA chama uma porta que não está publicada; em produção a origem é a mesma (`VITE_API_URL=""`) · same origin in production.
- F5 numa rota da SPA dá 404 → falta o `try_files $uri $uri/ /index.html` · missing SPA fallback.
- `SECURE_SSL_REDIRECT` ligado em `http://localhost` → *redirect* infinito para `https://`; e o *health check* a receber `301` · switch HTTPS off by environment for the local run and exempt the health check.
- `ALLOWED_HOSTS` sem `localhost` → `400 Bad Request` em tudo · every request is a 400.
- `/ws/` sem `Upgrade`/`Connection` no Nginx, ou Uvicorn sem a biblioteca `websockets` → o *socket* responde `404` · the WebSocket handshake fails.
- `test:unit` sem `-- --run` no CI → o Vitest fica em modo *watch* e o *job* nunca acaba · Vitest stays in watch mode.
- `schema.yaml` regenerado e `schema.d.ts` esquecido → os tipos mentem; aconteceu nesta referência entre a Ficha 04 e a Ficha 05, e foi o CI que o apanhou · a stale generated client; CI catches it.
- O Nginx resolve `web` **ao arrancar**: depois de recriar a API, `docker compose restart nginx` · Nginx resolves upstream names at start-up.

---

# Ficha 05 — Fora do pedido/resposta: tarefas, tempo real e JSONB · Outside request/response: tasks, real time and JSONB

Aula 07 (16/11/2026) · solução de referência · reference solution — construída sobre `ficha-04/` · built on top of `ficha-04/`. Só o **backend** muda; a SPA de `frontend/` é a da Ficha 04, intacta · only the **backend** changes; the SPA in `frontend/` is Ficha 04's, untouched.

**PT** — O `pay` continua síncrono, mas o **recibo** sai num *worker* Celery (idempotente, com *retries*, enfileirado no `on_commit`); um **relatório** de encomendas responde `202 Accepted` e expõe o progresso em `/api/v1/tasks/<id>/` (só para o dono); as duas tarefas **avisam o utilizador** por WebSocket (Django Channels, JWT em `?token=`, um grupo por utilizador); o catálogo filtra pelo **JSONB** `attributes` com um índice GIN (`?attr=color:red`). Opcional implementado: cache da lista de categorias com invalidação por versão e cabeçalho `X-Cache`. Não implementados: SSE, a SPA a ouvir o socket, MongoDB, `celery beat`.
**EN** — `pay` stays synchronous, but the **receipt** goes out in a Celery worker (idempotent, with retries, enqueued in `on_commit`); an order **report** answers `202 Accepted` and exposes progress at `/api/v1/tasks/<id>/` (owner only); both tasks **notify the user** over a WebSocket (Django Channels, JWT in `?token=`, one group per user); the catalogue filters on the **JSONB** `attributes` with a GIN index (`?attr=color:red`). Optional part implemented: category-list cache with version-key invalidation and an `X-Cache` header. Not implemented: SSE, the SPA listening to the socket, MongoDB, `celery beat`.

```sh
cp env.example .env && docker compose up -d && uv sync      # PostgreSQL 16 + Redis 7
uv run python manage.py migrate && uv run python manage.py seed
uv run python manage.py runserver                 # 1 · Daphne (ASGI): HTTP + WebSocket em :8000
uv run celery -A config worker -l info            # 2 · o worker · the worker
uv run pytest                                     # 51 testes, sem Redis · 51 tests, no Redis needed
```

## Como foi feito · How it was built

```sh
uv add "celery[redis]" redis channels channels-redis daphne && uv add --dev pytest-asyncio
uv run python manage.py makemigrations shop --name ficha05_receipt_gin
uv run python manage.py spectacular --file schema.yaml
```

`compose.yaml` (serviço `redis`) · `config/celery.py` + `config/__init__.py` · `config/asgi.py` (`ProtocolTypeRouter`) · `config/settings/base.py` (`REDIS_URL`, `CELERY_*`, `CHANNEL_LAYERS`, `CACHES`; `daphne` e `channels` em `INSTALLED_APPS`) · `config/settings/test.py` (eager, em memória) · `shop/tasks.py` · `shop/services.py` (`on_commit`) · `shop/notify.py` · `shop/consumers.py` + `shop/routing.py` · `accounts/ws_auth.py` · `shop/views.py` (`OrdersReportView`, `TaskStatusView`, cache em `CategoryViewSet.list`) · `shop/cache.py` + `shop/signals.py` · `shop/filters.py` (`attr`) · `shop/models.py` + migração `0003` (`Payment.receipt_sent_at`, `GinIndex`) · `shop/management/commands/seed.py` (atributos por categoria) · testes em `shop/tests/test_tasks.py`, `test_realtime.py`, `test_catalogue_cache_jsonb.py` · `docs/decisions.md` · `docs/ficha-05.md`.

Um Redis, três bases · one Redis, three databases: `/0` fila e resultados do Celery · `/1` cache do Django · `/2` channel layer.

## O que se verifica · What to check

1. `POST /api/v1/orders/<id>/pay/` responde logo com `paid`; o log do *worker* mostra `send_order_receipt … succeeded` e o email · pay answers at once; the worker log shows the task and the email.
2. *Worker* parado: o `pay` continua a responder; `redis-cli LLEN celery` → `1`; ao ligar o *worker* o recibo sai · with the worker down the API still answers and the message waits.
3. `send_order_receipt.delay(<id>)` segunda vez → `already-sent`, um só email · idempotent.
4. `RECEIPT_FLAKY=1 uv run celery -A config worker -l info` → `Retry in 2s` e depois `succeeded` · one retry with backoff.
5. `POST /api/v1/reports/orders/` → **202** com `status_url` e `Location`; `GET` repetido → `PROGRESS {current,total}` e depois `SUCCESS` com `result` · 202 then progress then result.
6. O `status_url` com o token de outro cliente → **404**; gestor → 200 · task status is owner-scoped.
7. `new WebSocket('ws://localhost:8000/ws/notifications/?token=<access>')` → `{"event":"connected"}`; pagar → `order.paid`; relatório → `report.ready`; sem token → fecha com **4401** · WebSocket notifications, JWT at the handshake.
8. `GET /api/v1/products/?attr=color:red` → só os vermelhos; `EXPLAIN` com `enable_seqscan = off` → `Bitmap Index Scan on product_attributes_gin` · JSONB containment through the GIN index.
9. `curl -i /api/v1/categories/` duas vezes → `X-Cache: MISS`, `HIT`; editar uma categoria no admin → `MISS` · cache invalidated by a version bump.
10. `uv run pytest` → 51 verdes (36 das fichas anteriores + 15 novos), sem Redis; `ruff check` limpo; `check --deploy` limpo com `prod.py` · green without Redis.

## Erros comuns · Common mistakes

- `.delay()` dentro do `transaction.atomic` em vez de `on_commit` → `Payment.DoesNotExist` no *worker*, às vezes · enqueue after the commit.
- Passar o objeto `order` à tarefa em vez do id → erro de serialização, ou dados velhos · pass ids.
- Tarefa sem marca de idempotência → dois emails quando a mensagem é reentregue · make it idempotent.
- Sem `CELERY_TASK_ALWAYS_EAGER` em `test.py` → o `pytest` fica à espera de um broker · eager mode in tests.
- `"daphne"` fora do topo de `INSTALLED_APPS` → o `runserver` continua WSGI e o WebSocket dá 404 · daphne first.
- Importar `consumers`/`routing` em `asgi.py` antes de `get_asgi_application()` → `AppRegistryNotReady` · Django first.
- `ALLOWED_HOSTS` sem `localhost` → o `AllowedHostsOriginValidator` fecha o socket sem mensagem · origin must be allowed.
- `close(4401)` sem `accept()` antes → o browser vê `1006`, não `4401` · accept, then close with the code.
- Enviar o `refresh` em `?token=` → fica nos logs um token de 1 dia · only the short access token goes in a URL.
- Testes de WebSocket com `transaction=True` apagam o grupo `gestores` criado por migração → `get_or_create` na *fixture* · transactional tests flush migration data.
- `@cache_page` em `/orders/` → a lista de um cliente servida a outro · never cache per-user responses by URL.
- Calcular o relatório dentro da *view* → o `202` deixa de fazer sentido · the view only enqueues.

---

## Frontend (= Ficha 04) · frontend (= Ficha 04)

_Ficha 04 — SPA Vue autenticada · Authenticated Vue SPA (partes 1 e 2 · parts 1 and 2)_

Aulas 05 + 06 (02/11 e 09/11/2026) · solução de referência · reference solution — construída sobre `ficha-03/` · built on top of `ficha-03/`. O backend é o da Ficha 03 com **uma** alteração: `COMPONENT_SPLIT_REQUEST: True` no drf-spectacular (e o `schema.yaml` regenerado), para que os tipos gerados do OpenAPI tenham `…Request` sem os campos `read_only` · the backend is Ficha 03's with **one** change: `COMPONENT_SPLIT_REQUEST` (and a regenerated `schema.yaml`), so the generated request types drop the `read_only` fields. O que é novo está em **[`frontend/`](frontend/)**: parte 1 (Aula 05) lista e detalhe do catálogo; parte 2 (Aula 06) tipos gerados + `openapi-fetch`, *store* Pinia `auth` com *refresh*, login + *guard*, «as minhas encomendas» e formulário com erros por campo, 10 testes · part 1: list and detail; part 2: generated types, auth store with refresh, login + guard, my orders and an order form with field errors, 10 tests.

```sh
cp env.example .env && docker compose up -d && uv sync
uv run python manage.py migrate && uv run python manage.py seed
uv run python manage.py runserver                        # API em :8000 (CORS: http://localhost:5173)
cd frontend && cp env.example .env && npm install && npm run dev   # SPA em :5173
```

---

## Backend (= Ficha 03) · backend (= Ficha 03)

Aula 04 (26/10/2026) · solução de referência · reference solution — construída sobre `ficha-02/` · built on top of `ficha-02/`

**PT** — Os alunos entregaram o mesmo *fork* da Ficha 02 com a tag `ficha-03`. Não é a única resposta certa: comparem com o vosso código. Login e *refresh* com JWT (`djangorestframework-simplejwt`, access 30 min, refresh 1 dia, rotação + blacklist), `IsAuthenticated` por omissão, `/api/v1/me/`; papel **`gestores`** (grupo criado por migração de dados) com `IsGestor`/`IsGestorOrReadOnly`; encomendas filtradas ao cliente (**alheia = 404**) e `IsOwnerOrGestor` em `pay`/`cancel`/`PATCH`; `customer`/`status`/`total` só de leitura; CORS com lista explícita, throttling `auth` 10/min no login, Argon2, `check --deploy` limpo em `prod.py`; e o teste de autorização parametrizado por papel. Opcional implementado: nenhum (CSP, allauth e audit log ficam como exercício — ver os slides da Aula 04).
**EN** — Students submitted the same Ficha 02 fork tagged `ficha-03`. Not the only correct answer: compare it with your own code. JWT login and refresh (simplejwt, 30-min access, 1-day refresh, rotation + blacklist), `IsAuthenticated` by default, `/api/v1/me/`; **`gestores`** role (group from a data migration) with `IsGestor`/`IsGestorOrReadOnly`; orders filtered to the caller (**someone else's = 404**) and `IsOwnerOrGestor` on `pay`/`cancel`/`PATCH`; `customer`/`status`/`total` read-only; explicit CORS allowlist, `auth` throttle 10/min on login, Argon2, clean `check --deploy` on `prod.py`; and the role-parametrised authorization test. Optional parts not implemented (CSP, allauth, audit log stay as exercises — see the Aula 04 slides).

```sh
cp env.example .env && docker compose up -d && uv sync
uv run python manage.py migrate                     # + tabelas da blacklist, grupo "gestores" · blacklist tables, group
uv run python manage.py seed && uv run python manage.py createsuperuser
uv run python manage.py runserver
curl -s localhost:8000/api/v1/orders/                                   # 401 (Problem Details)
curl -s -X POST localhost:8000/api/v1/auth/token/ -H "Content-Type: application/json" \
  -d '{"username":"ana","password":"<a password do seed>"}'              # {"access":…,"refresh":…}
curl -s localhost:8000/api/v1/me/ -H "Authorization: Bearer <access>"   # {"id":…,"username":"ana","groups":[]}
uv run pytest                                       # 36 testes verdes · 36 green tests
DJANGO_SETTINGS_MODULE=config.settings.prod ALLOWED_HOSTS=shop.example \
  uv run python manage.py check --deploy            # System check identified no issues
```

> O `seed` cria `ana`, `bruno`, `carla` com a password `pass1234` da `UserFactory` (só para dev) · the seed users use the factory password `pass1234` (dev only). Para testar como gestor: admin → Users → Groups → `gestores` · to test as a manager, add a user to the `gestores` group in the admin.

## Como foi feito · How it was built

```sh
uv add djangorestframework-simplejwt django-cors-headers argon2-cffi
uv run python manage.py makemigrations shop --empty --name group_gestores   # RunPython → Group "gestores"
uv run python manage.py migrate
uv run python manage.py spectacular --file schema.yaml
```

`config/settings/base.py` (`REST_FRAMEWORK` auth/permissões/throttle, `SIMPLE_JWT`, `CORS_*`, `PASSWORD_HASHERS`, validador a 12, `SECRET_KEY_FALLBACKS`) · `config/settings/prod.py` (HSTS 1 ano + preload) · `accounts/views.py` (`ThrottledTokenView`, `MeView`) · `config/urls.py` · `shop/permissions.py` · `shop/migrations/0002_group_gestores.py` · `shop/views.py` (queryset filtrado, `perform_create`, `get_serializer_class`) · `shop/serializers.py` (`read_only_fields`, `GestorOrderSerializer`) · testes em `accounts/tests/test_jwt.py`, `accounts/tests/test_hardening.py`, `shop/tests/test_auth.py` (+ `conftest.py` com os três atores) · `docs/decisions.md` · `docs/ficha-03.md`.

## O que se verifica · What to check

1. `GET /api/v1/orders/` sem token → **401** com corpo Problem Details; com `Bearer` → 200 e **só as encomendas do cliente** · 401 without a token; only the caller's orders with one.
2. `POST /api/v1/auth/token/` → par `access`/`refresh`; o *refresh* repetido com o **mesmo** token → 401 «Token is blacklisted» · reusing the old refresh token fails.
3. `GET /api/v1/me/` → `{"id","username","groups"}` · the SPA's "who am I".
4. `/api/v1/categories/` e `/api/v1/products/` leem-se **sem** token (`AllowAny`/`IsGestorOrReadOnly`, com comentário); `POST /products/` → 401 anónimo, **403** cliente, 201 gestor · public catalogue, writes for managers.
5. `GET /api/v1/orders/<id de outro>/` e `POST …/pay/` como cliente → **404**, não 403 · a foreign order is a 404.
6. `PATCH /orders/<minha>/ {"status":"paid"}` → 200 e o `status` **não muda** (`read_only_fields`); `POST /orders/` com `customer` de outro → o dono é o `request.user` · server-owned fields.
7. `MIDDLEWARE[0]` é o `CorsMiddleware`; `OPTIONS` com `Origin: http://localhost:5173` → 200 com `Access-Control-Allow-Origin` · preflight works for the SPA origin.
8. 11 logins errados seguidos → `401 ×10` e depois **429** · throttled after ten attempts.
9. `check --deploy` com `config.settings.prod` → `System check identified no issues (0 silenced)` (inclui os avisos do drf-spectacular: `queryset = Model.objects.none()` nos viewsets com `get_queryset`, `@extend_schema` na `MeView`) · zero warnings, spectacular's included.
10. `uv run pytest` → 36 verdes: 12 da Ficha 02 (os de API agora autenticados) + 3 JWT + 4 hardening + 17 da matriz endpoint × papel · 36 green.
11. `docs/decisions.md` com os tempos de vida, onde a SPA guarda o token e porquê, e a matriz; `docs/ficha-03.md` com as duas respostas · decisions and answers.

## Erros comuns · Common mistakes

- `CorsMiddleware` depois do `CommonMiddleware` → o *preflight* leva 401 e a SPA nunca chega a fazer o pedido · CORS middleware must be first.
- `IsAuthenticated` por omissão sem reabrir o catálogo → `/api/v1/products/` dá 401 e a SPA da Aula 05 não lista produtos · reopen the catalogue on purpose.
- `SessionAuthentication` removida → a Browsable API passa a 403 em `POST` e a culpa cai no JWT · keep session auth for the admin and Browsable API.
- Grupo criado à mão no admin e não por migração → `Group.DoesNotExist` na CI · create the group in a data migration.
- `has_object_permission` sem filtro no queryset → a lista mostra tudo; filtro sem `has_object_permission` → `PATCH` num id conhecido passa; encomenda alheia a dar 403 em vez de 404 · both layers, 404 not 403.
- `is_gestor()` chamado duas vezes por pedido (queryset + serializer) sem cache → uma query a mais; o teste «≤ 4 queries» apanha-o · cache the group check on the user.
- `throttle_scope` sem `throttle_classes` na subclasse da vista de token → a *rate* `auth` nunca se aplica · both attributes on the subclass.
- `check --deploy` corrido com `dev.py`, ou contra `prod.py` com uma `SECRET_KEY` curta (W009) · run it against prod with a real-length key.
- Viewsets só com `get_queryset` sem `queryset = Model.objects.none()` → avisos do drf-spectacular no `check` e `id` sem tipo no Swagger · schema generation needs the model hint.
- `SECRET_KEY` com valor por omissão em `base.py` «para os testes passarem» → vai para o git · never a default secret in code.
