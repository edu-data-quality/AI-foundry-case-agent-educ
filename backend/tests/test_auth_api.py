"""Testes da autenticação e autorização por role (issue #3).

Cobre os critérios de aceitação:
- login ok devolve JWT com a role correta;
- senha errada / usuário inexistente → 401;
- sem token / token inválido / token expirado → 401;
- aluno autenticado não acessa rota ADMIN → 403; admin acessa → 200;
- perfil (`/api/auth/me`) expõe a role e o vínculo de aluno do token.
"""

from datetime import timedelta

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import auth
from app.api.deps import requer_admin
from app.api.routes.auth import router as auth_router
from app.db.models import RoleUsuario, Usuario
from app.db.session import get_db
from app.repositories.alunos import AlunoRepository
from app.repositories.usuarios import UsuarioRepository
from app.security import hash_senha

# App de teste: rotas reais de auth + um endpoint protegido por ADMIN (canário).
_test_admin_router = APIRouter()


@_test_admin_router.get("/admin/panel")
def _painel_admin(usuario: Usuario = Depends(requer_admin)) -> dict:
    return {"admin_id": str(usuario.id)}


_test_app = FastAPI()
_test_app.include_router(auth_router)
_test_app.include_router(_test_admin_router)


def _montar_aluno_admin(sessao: Session) -> tuple[Usuario, Usuario]:
    """Cria um aluno demo vinculado e um admin; retorna os dois usuários."""
    aluno_repo = AlunoRepository(sessao)
    aluno = aluno_repo.criar(
        cpf="11122233344",
        nome_completo="Aluna Teste",
        email="aluna@exemplo.com",
    )
    usuarios = UsuarioRepository(sessao)
    admin = usuarios.criar(
        login="admin", senha_hash=hash_senha("admin123"), role=RoleUsuario.ADMIN
    )
    aluno_user = usuarios.criar(
        login="aluna",
        senha_hash=hash_senha("aluna123"),
        role=RoleUsuario.ALUNO,
        aluno_id=aluno.id,
    )
    return admin, aluno_user


@pytest.fixture()
def client(sessao: Session) -> TestClient:
    """Client com o banco de teste e a sessão única por request."""
    _test_app.dependency_overrides[get_db] = lambda: sessao
    yield TestClient(_test_app)
    _test_app.dependency_overrides.clear()


def _fazer_login(client: TestClient, login: str, senha: str) -> None:
    """Autentica e anexa o header Bearer ao client."""
    response = client.post("/api/auth/login", json={"login": login, "senha": senha})
    assert response.status_code == 200
    token = response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})


def test_login_ok_devolve_jwt(sessao: Session, client: TestClient) -> None:
    admin, _ = _montar_aluno_admin(sessao)
    response = client.post(
        "/api/auth/login", json={"login": "admin", "senha": "admin123"}
    )

    assert response.status_code == 200
    corpo = response.json()
    assert corpo["token_type"] == "bearer"
    assert corpo["role"] == "ADMIN"
    assert corpo["expires_in"] == 60 * 60

    claims = auth.decodificar_token(corpo["access_token"])
    assert claims["sub"] == str(admin.id)
    assert claims["role"] == "ADMIN"


def test_login_senha_errada_retorna_401(sessao: Session, client: TestClient) -> None:
    _montar_aluno_admin(sessao)
    response = client.post("/api/auth/login", json={"login": "admin", "senha": "errada"})
    assert response.status_code == 401


def test_login_usuario_inexistente_retorna_401(
    sessao: Session, client: TestClient
) -> None:
    _montar_aluno_admin(sessao)
    response = client.post("/api/auth/login", json={"login": "nao-existe", "senha": "x"})
    assert response.status_code == 401


def test_me_sem_token_retorna_401(sessao: Session, client: TestClient) -> None:
    _montar_aluno_admin(sessao)
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "token ausente"


def test_me_token_invalido_retorna_401(sessao: Session, client: TestClient) -> None:
    _montar_aluno_admin(sessao)
    client.headers.update({"Authorization": "Bearer assinatura.falsa.errada"})
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "token inválido"


def test_token_expirado_retorna_401(sessao: Session, client: TestClient) -> None:
    admin, _ = _montar_aluno_admin(sessao)
    token_expirado = auth.criar_token(
        usuario_id=str(admin.id),
        login=admin.login,
        role=RoleUsuario.ADMIN.value,
        tempo_de_vida=timedelta(seconds=-1),
    )
    client.headers.update({"Authorization": f"Bearer {token_expirado}"})
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "token expirado"


def test_me_do_aluno_expoe_vinculo_e_role(
    sessao: Session, client: TestClient
) -> None:
    _, aluno = _montar_aluno_admin(sessao)
    _fazer_login(client, "aluna", "aluna123")
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    corpo = response.json()
    assert corpo["role"] == "ALUNO"
    assert corpo["login"] == "aluna"
    assert corpo["aluno_id"] == str(aluno.aluno_id)


def test_me_do_admin_expoe_role_sem_aluno(
    sessao: Session, client: TestClient
) -> None:
    _montar_aluno_admin(sessao)
    _fazer_login(client, "admin", "admin123")
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"
    assert response.json()["aluno_id"] is None


def test_aluno_nao_acessa_rota_admin(sessao: Session, client: TestClient) -> None:
    _montar_aluno_admin(sessao)
    _fazer_login(client, "aluna", "aluna123")
    response = client.get("/admin/panel")
    assert response.status_code == 403
    assert response.json()["detail"] == "acesso restrito ao administrador"


def test_admin_acessa_rota_admin(sessao: Session, client: TestClient) -> None:
    admin, _ = _montar_aluno_admin(sessao)
    _fazer_login(client, "admin", "admin123")
    response = client.get("/admin/panel")
    assert response.status_code == 200
    assert response.json() == {"admin_id": str(admin.id)}


def test_rotas_reais_incluidas_no_app_principal() -> None:
    """O app real expõe /api/auth/login e /api/auth/me."""
    from app.main import app

    schema = app.openapi()["paths"]
    assert "/api/auth/login" in schema
    assert "/api/auth/me" in schema