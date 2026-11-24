"""CORS para o front Angular (issue #16 — bug do preflight 405 no login).

O `ng serve` roda em `http://localhost:4200`, origem diferente da API
(`:8000`). Sem CORS o navegador envia `OPTIONS /api/auth/login` e recebia
405, bloqueando o login.
"""

from fastapi.testclient import TestClient

from app.main import app

ORIGEM_DEV = "http://localhost:4200"


def _preflight(origem: str):
    """Simula o preflight do navegador para `POST /api/auth/login`."""
    return TestClient(app).options(
        "/api/auth/login",
        headers={
            "Origin": origem,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )


def test_preflight_do_login_libera_origem_do_ng_serve() -> None:
    response = _preflight(ORIGEM_DEV)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGEM_DEV
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_preflight_libera_tambem_127_0_0_1() -> None:
    response = _preflight("http://127.0.0.1:4200")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:4200"


def test_preflight_de_origem_desconhecida_nao_e_liberado() -> None:
    response = _preflight("http://origem-nao-configurada.example")

    assert "access-control-allow-origin" not in response.headers


def test_resposta_real_inclui_header_de_origem_permitida() -> None:
    """Resposta de erro também passa pelo CORS (ex: 401 de credencial inválida)."""
    response = TestClient(app).post(
        "/api/auth/login",
        json={"login": "ninguem", "senha": "errada"},
        headers={"Origin": ORIGEM_DEV},
    )

    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == ORIGEM_DEV
