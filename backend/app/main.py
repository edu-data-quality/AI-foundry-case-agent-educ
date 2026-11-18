"""Pacote principal da API do Assistente Académico EAD."""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.routes.admin import router as admin_router
from app.api.routes.aluno import router as aluno_router
from app.api.routes.auth import router as auth_router
from app.api.routes.conversas import router as conversas_router
from app.api.routes.declaracoes import router as declaracoes_router
from app.api.routes.financeiro import router as financeiro_router
from app.conversas import job_ativo, loop_timeout_conversas


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Sobe o job de timeout das sessões e o encerra no shutdown."""
    tarefa: asyncio.Task[None] | None = None
    if job_ativo():
        tarefa = asyncio.create_task(loop_timeout_conversas())
    try:
        yield
    finally:
        if tarefa is not None:
            tarefa.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await tarefa


app = FastAPI(
    title="Assistente Académico EAD",
    description="Backend do Assistente Académico EAD (Azure AI Foundry case).",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(aluno_router)
app.include_router(financeiro_router)
app.include_router(declaracoes_router)
app.include_router(conversas_router)
app.include_router(admin_router)
