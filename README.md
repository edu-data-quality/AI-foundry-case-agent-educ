# Assistente Académico EAD — Azure AI Foundry Case

MVP de testes que demonstra a integração ponta a ponta entre **Azure AI Foundry**
(agente GPT-4o com Function Calling), **RAG** sobre documentos estáticos e um
**painel administrativo** para simular o ciclo de vida do aluno.

> Este é o segundo case deste repositório. O case anterior (TriagemIA — orquestração
> de agentes com mock APIs) está arquivado em [`legacy/triagemia/`](legacy/triagemia/README.md).

## Arquitetura

```
frontend/ (Angular)  ──►  backend/ (FastAPI)  ──►  Azure AI Foundry (agente)
```

- **backend/** — API FastAPI responsável por expor as Tools (Function Calling) e
  gerir as regras de negócio (alunos, disciplinas, mensalidades).
- **frontend/** — Angular com Portal do Aluno (Chat + Dashboard) e Painel
  Administrativo (CRUD + Simulador).

## Stack

| Camada       | Tecnologia          |
|--------------|---------------------|
| Backend/API  | Python 3.12 · FastAPI · Uvicorn |
| Front-end    | Angular 19 · Node 22 |
| Base de dados| PostgreSQL (ou SQLite em testes) |
| IA           | Azure AI Foundry · GPT-4o · RAG · OpenAPI Tools |

## Estrutura do repositório

```
.
├── backend/                 # API FastAPI
│   ├── app/
│   │   ├── main.py          # Cria a aplicação e registra os routers
│   │   └── api/
│   │       └── health.py    # Router de healthcheck
│   ├── tests/               # Testes (pytest)
│   ├── Dockerfile           # Dev container (uvicorn --reload)
│   ├── .dockerignore
│   ├── pyproject.toml       # Config do pytest
│   ├── requirements.txt     # Dependências de runtime
│   └── requirements-dev.txt # Dependências de dev (inclui runtime)
├── frontend/                # App Angular (shell)
│   ├── src/
│   └── angular.json
├── docs/                    # PRD, ADRs e documentação
├── legacy/triagemia/        # Case anterior (TriagemIA) — arquivado
├── docker-compose.yml       # backend + db (PostgreSQL 16)
├── .env.example             # Variáveis de ambiente (referência)
└── README.md
```

## Como rodar

### Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv          # se ainda não houver
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

Servidor em `http://127.0.0.1:8000` — healthcheck em `GET /health`:

```bash
curl http://127.0.0.1:8000/health
# {"status": "ok"}
```

**Testes:**

```bash
cd backend
.venv/bin/pytest
```

### Frontend (Angular)

```bash
cd frontend
npm install                   # se ainda não houver node_modules
npx ng serve
```

Servidor em `http://localhost:4200` (shell vazio por enquanto).

### Docker (backend + PostgreSQL)

Subir o ambiente completo (backend na porta 8000 + PostgreSQL 16 healthy):

```bash
cp .env.example .env     # opcional: ajuste credenciais/portas
docker compose up -d
curl http://localhost:8000/health
# {"status": "ok"}
```

- Backend: `backend/Dockerfile`, roda `uvicorn --reload`; `backend/app` e
  `backend/tests` são montados por volume (edição reflete no reload).
- Banco: serviço `db` (postgres:16-alpine), volume `ead_pgdata` persistente.
  O backend só inicia após o healthcheck do banco.
- Portas no host parametrizáveis: `BACKEND_PORT` (default 8000) e
  `POSTGRES_PORT` (default 5432). Ex.: `BACKEND_PORT=8005 docker compose up -d`.
- Derrubar: `docker compose down` (mantém o volume de dados; use
  `down -v` para apagar os dados também).

> Importante: sem Docker, o fluxo `.venv` acima continua válido.

## Variáveis de ambiente

Copie `.env.example` para `.env` (na raiz) e preencha conforme o ambiente.

| Variável                   | Descrição                                            |
|----------------------------|------------------------------------------------------|
| `AZURE_OPENAI_API_KEY`     | Chave do recurso Azure OpenAI                        |
| `AZURE_OPENAI_ENDPOINT`    | Endpoint do recurso (`https://<x>.openai.azure.com/`) |
| `AZURE_OPENAI_API_VERSION` | Versão da API (default `2024-10-21`)                 |
| `AZURE_OPENAI_DEPLOYMENT`  | Nome do deployment (default `gpt-4o`)                |
| `POSTGRES_USER`            | Usuário do banco no compose (default `ead`)          |
| `POSTGRES_PASSWORD`        | Senha do banco no compose (default `ead`)            |
| `POSTGRES_DB`              | Base no compose (default `ead`)                      |
| `POSTGRES_PORT`            | Porta do Postgres no host (default `5432`)           |
| `DATABASE_URL`             | URL SQLAlchemy da base (`postgresql+psycopg://…`)    |
| `BACKEND_PORT`             | Porta do backend no host (default `8000`)            |
| `TRIAGEM_LIMIAR_CONFIANCA` | Limiar de confiança p/ HITL (default `0.8`)          |
| `TRIAGEM_OFFLINE`          | `1` usa classificador offline (sem Azure)            |
| `MOCK_API_URL`             | Base URL do mock (default `http://127.0.0.1:8000`)   |
| `MOCK_API_TIMEOUT`         | Timeout das chamadas (default `10`)                  |

> As variáveis `TRIAGEM_*` e `MOCK_*` vêm do case arquivado
> (`legacy/triagemia/`) e serão removidas quando o novo backend substituí-las.

## Roadmap

Detalhes do produto, épicos e histórico das decisões estão em
[`docs/PRD.md`](docs/PRD.md). O trabalho é rastreado em GitHub Issues
(milestones = épicos do PRD).