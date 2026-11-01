"""Pacote principal da API do Assistente Académico EAD."""

from fastapi import FastAPI

from app.api.health import router as health_router

app = FastAPI(
    title="Assistente Académico EAD",
    description="Backend do Assistente Académico EAD (Azure AI Foundry case).",
    version="0.1.0",
)

app.include_router(health_router)