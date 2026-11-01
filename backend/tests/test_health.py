"""Testes do healthcheck do backend."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthcheck_ok() -> None:
    """GET /health retorna 200 com status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}