# Ficha 05 — como correr, EXPLAIN e perguntas de reflexão · how to run, EXPLAIN and reflection questions

## Como correr · How to run

```sh
docker compose up -d                              # PostgreSQL + Redis
uv run python manage.py migrate && uv run python manage.py seed
uv run python manage.py runserver                 # 1 · API + WebSocket (Daphne)
uv run celery -A config worker -l info            # 2 · worker
```

Três processos: a API (ASGI), o *worker* e o Redis (mais o PostgreSQL). Sem o *worker* a API continua a responder; as tarefas esperam no Redis · three processes: the API (ASGI), the worker and Redis (plus PostgreSQL). Without the worker the API still answers; tasks wait in Redis.

## Parte 4 — `EXPLAIN`

```sql
EXPLAIN SELECT id FROM shop_product WHERE attributes @> '{"color": "red"}';
-- Seq Scan on shop_product  (cost=0.00..12.25 rows=2 width=8)
--   Filter: (attributes @> '{"color": "red"}'::jsonb)

SET enable_seqscan = off;
EXPLAIN SELECT id FROM shop_product WHERE attributes @> '{"color": "red"}';
-- Bitmap Heap Scan on shop_product  (cost=17.24..22.58 rows=2 width=8)
--   Recheck Cond: (attributes @> '{"color": "red"}'::jsonb)
--   ->  Bitmap Index Scan on product_attributes_gin  (cost=0.00..17.24 rows=2 width=0)
--         Index Cond: (attributes @> '{"color": "red"}'::jsonb)
```

PT — Com 40 linhas a tabela cabe numa página: lê-la toda custa menos (12.25) do que percorrer o índice e depois ir à tabela (22.58), por isso o *planner* escolhe o *seq scan* — e bem. O índice passa a ganhar quando a tabela cresce e o filtro é seletivo.
EN — With 40 rows the table fits in one page: reading it all (12.25) is cheaper than walking the index and then the heap (22.58), so the planner rightly picks the sequential scan. The index wins once the table grows and the filter is selective.

## Perguntas de reflexão · Reflection questions

**1. O *worker* envia o email do recibo e morre antes de gravar `receipt_sent_at`. Com `acks_late=True`, o que acontece a seguir, e o que recebe o cliente? E com `acks_late=False`? Qual dos dois erros preferem, e o que mudaria se a tarefa fosse cobrar um cartão?**

PT — Com `acks_late=True` a mensagem ainda não foi confirmada: o broker volta a entregá-la, a transação anterior fez rollback (a marca não ficou), a tarefa corre outra vez e o cliente recebe **dois recibos**. Com `acks_late=False` a mensagem foi confirmada à chegada: ninguém a repete; neste cenário o cliente recebeu um email, mas se o *worker* tivesse morrido **antes** de enviar não receberia nenhum, e a marca nunca seria gravada. Para um recibo prefiro *pelo menos uma vez*: um email repetido incomoda, um recibo em falta é um pedido de apoio. Para cobrar um cartão nenhum dos dois serve sozinho — duas cobranças são inaceitáveis e uma cobrança em falta também: mantinha `acks_late=True` e enviava ao fornecedor uma **chave de idempotência** (o id do pagamento), para que a segunda chamada devolvesse o resultado da primeira em vez de cobrar outra vez.

EN — With `acks_late=True` the message was never acknowledged: the broker redelivers it, the earlier transaction rolled back (no mark), the task runs again and the customer gets **two receipts**. With `acks_late=False` it was acknowledged on arrival and is never retried; here the customer got one email, but had the worker died **before** sending they would get none. For a receipt I prefer at-least-once: a duplicate email is an annoyance, a missing receipt is a support ticket. For charging a card neither is enough alone — I would keep `acks_late=True` and send the provider an **idempotency key** (the payment id), so the second call returns the first call's result instead of charging again.

**2. `Product.attributes` é JSONB. Deem um atributo que deveria passar a coluna e digam porquê; e descrevam um cenário em que moveriam o catálogo para uma base de documentos, dizendo o que perderiam em relação às encomendas.**

PT — `color`, se a loja passar a ter um filtro de cor em todas as listagens e a ordenar ou agrupar por ela: uma chave que quase todas as linhas têm e que quase todas as queries usam é uma coluna disfarçada — como coluna ganha tipo, `CHECK`/`choices`, um índice B-tree barato e estatísticas para o *planner*. Moveria o catálogo para o MongoDB se ele crescesse para milhões de produtos com formas muito diferentes, alimentado por muitos fornecedores com escrita intensa e lido em várias regiões — o caso em que o *sharding* nativo e o documento «com a forma do ecrã» compensam. Perderia a transação única que hoje cobre «criar a encomenda e validar/baixar o stock», as chaves estrangeiras de `OrderItem.product` (passaria a guardar um id sem garantia e uma cópia do nome e do preço) e os joins nos relatórios; e ganharia duas fontes de verdade para sincronizar.

EN — `color`, once the shop filters by colour on every listing and sorts or groups by it: a key nearly every row has and nearly every query uses is a column in disguise — as a column it gains a type, a `CHECK`/`choices`, a cheap B-tree index and planner statistics. I would move the catalogue to MongoDB if it grew to millions of products with very different shapes, fed by many suppliers with heavy writes and read from several regions — where native sharding and screen-shaped documents pay off. I would lose the single transaction that today covers "create the order and validate/decrement stock", the foreign key behind `OrderItem.product` (an unchecked id plus a copy of name and price instead) and joins in reports; and I would gain two sources of truth to keep in sync.
