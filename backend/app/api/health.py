"""Endpoint de healthcheck."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def healthcheck() -> dict:
    """Healthcheck usado por orchestrators e testes."""
    return {"status": "ok"}