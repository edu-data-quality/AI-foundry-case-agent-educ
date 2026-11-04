"""Pacote principal da API do Assistente Académico EAD."""

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.routes.auth import router as auth_router

app = FastAPI(
    title="Assistente Académico EAD",
    description="Backend do Assistente Académico EAD (Azure AI Foundry case).",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(auth_router)