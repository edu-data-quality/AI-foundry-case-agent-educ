# ADR-0001: Ambiente de desenvolvimento backend com Docker

- **Data:** 2026-11-01
- **Status:** Aceito
- **Decisores:** time do projeto (solicitado pelo usuário durante o Setup, issue #1)

## Contexto

O monorepo inicia a vida com `backend/` (FastAPI) e `frontend/` (Angular). As
APIs ainda não existem; elas serão construídas a partir do Épico 1 (issues #2–#8).
Sem padronização de ambiente, cada desenvolvedor sobe o backend com Python/venv
próprio, variando versões e dependências — e os testes rodam contra ambientes
diferentes.

## Decisão

Dockerizar o backend **já no Setup (issue #1)**, antes de escrever as APIs:

- `backend/Dockerfile` — imagem Python 3.12-slim, executa `uvicorn` com `--reload`.
- `docker-compose.yml` na raiz — serviço `backend` com porta `8000` e volumes que
  montam `backend/app` e `backend/tests` para o reload refletir alterações.
- `.dockerignore` em `backend/` — exclui `.venv`, `__pycache__`, caches.

Quando o Épico 1 criar a camada de dados (issue #2), o backend usa o alvo
PostgreSQL já provisionado no compose.

## Atualização (2026-11-01)

A pedido do usuário, o serviço `db` (PostgreSQL 16) **já entrou no compose
durante o Setup** (issue #1): imagem `postgres:16-alpine`, volume persistente
(`ead_pgdata`) e healthcheck. O backend sobe com `depends_on: service_healthy`.
Isso antecipa o ambiente de dados para dev/testes antes da camada de acesso
(issue #2), que passa a mirar `postgresql+psycopg://...` no compose.

## Atualização (2026-11-02) — camada de dados e `.env`

Com a issue #2, o backend passou a carregar `.env` via `load_dotenv()` em
`backend/app/db/session.py` e `backend/alembic/env.py` (variáveis já exportadas
pelo compose/CI têm precedência).

- `backend/Dockerfile` copia `alembic.ini` e `alembic/` para a imagem.
- `docker-compose.yml` monta `backend/alembic` como volume: migrações são
  editadas sem rebuild.
- `.env.example` mantém `DATABASE_URL` comentado: sem Docker, o fallback é
  SQLite local. No compose, a URL do Postgres é injetada no serviço `backend`.
- O seed demo se recusa a rodar com `APP_ENV=production`.

## Consequências

- **Positivas:** mesmo ambiente para dev e testes; comando único
  (`docker compose up`) sobe o backend; CI futuro reaproveita o Dockerfile;
  a migração para Postgres em container é incremental.
- **Negativas:** custo de imagem/minutagem no fluxo local; para devs sem Docker,
  o fluxo `.venv` documentado continua válido desde que `DATABASE_URL` fique
  comentado no `.env` (fallback SQLite) — nenhuma das duas vias é obrigatória.
- **Frontend:** fica fora do Docker neste momento; executa com `ng serve` local.