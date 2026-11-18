"""Testes da autenticação e autorização por role (issue #3).

Cobre os critérios de aceitação:
- login ok devolve JWT com a role correta;
- senha errada / usuário inexistente → 401;
- sem token / token inválido / token expirado → 401;
- aluno autenticado não acessa rota ADMIN → 403; admin acessa → 200;
- perfil (`/api/auth/me`) expõe a role e o vínculo de aluno do token.
"""

from datetime import timedelta
import uuid

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import auth
from app.api.deps import requer_admin
from app.api.routes.auth import router as auth_router
from app.db.models import MotivoFechamento, RoleUsuario, StatusConversa, Usuario
from app.db.session import get_db
from app.repositories.alunos import AlunoRepository
from app.repositories.conversas import ConversaRepository
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
    """O app real expõe /api/auth/login, /api/auth/logout e /api/auth/me."""
    from app.main import app

    schema = app.openapi()["paths"]
    assert "/api/auth/login" in schema
    assert "/api/auth/logout" in schema
    assert "/api/auth/me" in schema


def test_login_do_aluno_abre_sessao_de_chat(
    sessao: Session, client: TestClient
) -> None:
    _, aluno = _montar_aluno_admin(sessao)

    response = client.post(
        "/api/auth/login", json={"login": "aluna", "senha": "aluna123"}
    )

    assert response.status_code == 200
    conversa_id = response.json()["conversa_id"]
    assert conversa_id is not None
    conversa = ConversaRepository(sessao).buscar_por_id(uuid.UUID(conversa_id))
    assert conversa is not None
    assert conversa.aluno_id == aluno.aluno_id
    assert conversa.status is StatusConversa.ABERTA


def test_login_do_admin_nao_abre_sessao(sessao: Session, client: TestClient) -> None:
    _montar_aluno_admin(sessao)

    response = client.post(
        "/api/auth/login", json={"login": "admin", "senha": "admin123"}
    )

    assert response.status_code == 200
    assert response.json()["conversa_id"] is None


def test_logout_fecha_a_sessao_aberta(sessao: Session, client: TestClient) -> None:
    _montar_aluno_admin(sessao)
    login = client.post(
        "/api/auth/login", json={"login": "aluna", "senha": "aluna123"}
    ).json()
    client.headers.update({"Authorization": f"Bearer {login['access_token']}"})

    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json()["conversa_id"] == login["conversa_id"]
    conversa = ConversaRepository(sessao).buscar_por_id(
        uuid.UUID(login["conversa_id"])
    )
    assert conversa.status is StatusConversa.FECHADA
    assert conversa.motivo_fechamento is MotivoFechamento.LOGOUT
    assert conversa.data_fim is not None


def test_logout_sem_sessao_aberta_e_idempotente(
    sessao: Session, client: TestClient
) -> None:
    """Logout repetido não erra e devolve sempre o id da sessão encerrada."""
    _montar_aluno_admin(sessao)
    login = client.post(
        "/api/auth/login", json={"login": "aluna", "senha": "aluna123"}
    ).json()
    client.headers.update({"Authorization": f"Bearer {login['access_token']}"})
    primeira = client.post("/api/auth/logout").json()

    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json()["conversa_id"] == primeira["conversa_id"]
    assert primeira["conversa_id"] == login["conversa_id"]


def test_logout_nao_quebra_com_sessao_ja_fechada(
    sessao: Session, client: TestClient
) -> None:
    """Corrida com o job de timeout: logout devolve o id, sem 409/500."""
    _montar_aluno_admin(sessao)
    login = client.post(
        "/api/auth/login", json={"login": "aluna", "senha": "aluna123"}
    ).json()
    client.headers.update({"Authorization": f"Bearer {login['access_token']}"})
    conversa = ConversaRepository(sessao).buscar_por_id(
        uuid.UUID(login["conversa_id"])
    )
    # Fecha por TIMEOUT antes do logout (o job ganhou a corrida).
    ConversaRepository(sessao).fechar(conversa.id, MotivoFechamento.TIMEOUT)

    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json()["conversa_id"] == login["conversa_id"]


def test_logout_sem_token_retorna_401(sessao: Session, client: TestClient) -> None:
    _montar_aluno_admin(sessao)

    assert client.post("/api/auth/logout").status_code == 401