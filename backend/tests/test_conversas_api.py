"""Testes do ciclo de vida das sessões de chat (issue #11).

Critérios de aceitação cobertos:
- login do aluno abre a sessão; logout fecha com motivo LOGOUT;
- uma única conversa ABERTA por aluno (reabrir retoma a mesma);
- job de timeout fecha por TIMEOUT após `THREAD_TIMEOUT_MIN` sem interação;
- listagem/detalhe disponíveis para auditoria, com escopo por role.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import auth
from app.api.routes.conversas import router as conversas_router
from app.conversas import fechar_conversas_inativas, timeout_minutos
from app.db.models import MotivoFechamento, RoleUsuario, StatusConversa, Usuario
from app.db.session import get_db
from app.repositories.alunos import AlunoRepository
from app.repositories.conversas import ConversaRepository
from app.repositories.usuarios import UsuarioRepository
from app.security import hash_senha

_test_app = FastAPI()
_test_app.include_router(conversas_router)


@pytest.fixture()
def client(sessao: Session) -> TestClient:
    _test_app.dependency_overrides[get_db] = lambda: sessao
    yield TestClient(_test_app)
    _test_app.dependency_overrides.clear()


def _montar_usuarios(sessao: Session) -> tuple[Usuario, Usuario, Usuario]:
    """Cria dois alunos (com usuários) e um admin."""
    alunos = AlunoRepository(sessao)
    aluno = alunos.criar(
        cpf="11122233344", nome_completo="Aluna Teste", email="aluna@exemplo.com"
    )
    outro = alunos.criar(
        cpf="55566677788", nome_completo="Outro Aluno", email="outro@exemplo.com"
    )
    usuarios = UsuarioRepository(sessao)
    admin = usuarios.criar(
        login="admin", senha_hash=hash_senha("admin123"), role=RoleUsuario.ADMIN
    )
    usuario_aluno = usuarios.criar(
        login="aluna",
        senha_hash=hash_senha("aluna123"),
        role=RoleUsuario.ALUNO,
        aluno_id=aluno.id,
    )
    usuario_outro = usuarios.criar(
        login="outro",
        senha_hash=hash_senha("outro123"),
        role=RoleUsuario.ALUNO,
        aluno_id=outro.id,
    )
    return admin, usuario_aluno, usuario_outro


def _autenticar(client: TestClient, usuario: Usuario) -> None:
    token = auth.criar_token(
        usuario_id=str(usuario.id), login=usuario.login, role=usuario.role.value
    )
    client.headers.update({"Authorization": f"Bearer {token}"})


def test_login_abre_conversa_aberta(sessao: Session, client: TestClient) -> None:
    _, usuario_aluno, _ = _montar_usuarios(sessao)
    _autenticar(client, usuario_aluno)

    response = client.post("/api/conversas")

    assert response.status_code == 200
    corpo = response.json()
    assert corpo["status"] == "ABERTA"
    assert corpo["aluno_id"] == str(usuario_aluno.aluno_id)
    assert corpo["data_inicio"] is not None
    assert corpo["data_fim"] is None
    assert corpo["motivo_fechamento"] is None
    assert corpo["thread_id_foundry"] is None


def test_reabrir_retoma_a_mesma_conversa(sessao: Session, client: TestClient) -> None:
    _, usuario_aluno, _ = _montar_usuarios(sessao)
    _autenticar(client, usuario_aluno)

    primeira = client.post("/api/conversas").json()
    segunda = client.post("/api/conversas").json()

    assert primeira["id"] == segunda["id"]
    assert len(ConversaRepository(sessao).listar(aluno_id=usuario_aluno.aluno_id)) == 1


def test_thread_id_do_foundry_e_registrado(sessao: Session, client: TestClient) -> None:
    _, usuario_aluno, _ = _montar_usuarios(sessao)
    _autenticar(client, usuario_aluno)

    corpo = client.post(
        "/api/conversas", json={"thread_id_foundry": "thread-abc"}
    ).json()
    assert corpo["thread_id_foundry"] == "thread-abc"

    retomada = client.post(
        "/api/conversas", json={"thread_id_foundry": "thread-abc"}
    ).json()
    assert retomada["id"] == corpo["id"]
    assert retomada["thread_id_foundry"] == "thread-abc"


def test_admin_nao_abre_sessao_de_aluno(sessao: Session, client: TestClient) -> None:
    admin, _, _ = _montar_usuarios(sessao)
    _autenticar(client, admin)

    assert client.post("/api/conversas").status_code == 403


def test_sem_token_nao_abre_conversa(client: TestClient) -> None:
    assert client.post("/api/conversas").status_code == 401


def test_logout_fecha_com_motivo(sessao: Session, client: TestClient) -> None:
    _, usuario_aluno, _ = _montar_usuarios(sessao)
    _autenticar(client, usuario_aluno)
    conversa = client.post("/api/conversas").json()

    response = client.post(f"/api/conversas/{conversa['id']}/fechar")

    assert response.status_code == 200
    corpo = response.json()
    assert corpo["status"] == "FECHADA"
    assert corpo["motivo_fechamento"] == "LOGOUT"
    assert corpo["data_fim"] is not None


def test_fechar_duas_vezes_devolve_409(sessao: Session, client: TestClient) -> None:
    _, usuario_aluno, _ = _montar_usuarios(sessao)
    _autenticar(client, usuario_aluno)
    conversa = client.post("/api/conversas").json()
    client.post(f"/api/conversas/{conversa['id']}/fechar")

    assert client.post(f"/api/conversas/{conversa['id']}/fechar").status_code == 409


def test_aluno_nao_fecha_sessao_de_outro(sessao: Session, client: TestClient) -> None:
    _, usuario_aluno, usuario_outro = _montar_usuarios(sessao)
    _autenticar(client, usuario_outro)
    conversa = client.post("/api/conversas").json()

    _autenticar(client, usuario_aluno)
    assert client.post(f"/api/conversas/{conversa['id']}/fechar").status_code == 403


def test_fechar_sessao_inexistente_devolve_404(
    sessao: Session, client: TestClient
) -> None:
    _, usuario_aluno, _ = _montar_usuarios(sessao)
    _autenticar(client, usuario_aluno)

    assert client.post(f"/api/conversas/{uuid.uuid4()}/fechar").status_code == 404


def test_apos_logout_novo_login_abre_outra_sessao(
    sessao: Session, client: TestClient
) -> None:
    _, usuario_aluno, _ = _montar_usuarios(sessao)
    _autenticar(client, usuario_aluno)
    primeira = client.post("/api/conversas").json()
    client.post(f"/api/conversas/{primeira['id']}/fechar")

    segunda = client.post("/api/conversas").json()

    assert segunda["id"] != primeira["id"]
    assert segunda["status"] == "ABERTA"


def test_listagem_do_aluno_mostra_apenas_as_proprias(
    sessao: Session, client: TestClient
) -> None:
    _, usuario_aluno, usuario_outro = _montar_usuarios(sessao)
    _autenticar(client, usuario_outro)
    client.post("/api/conversas")
    _autenticar(client, usuario_aluno)
    propria = client.post("/api/conversas").json()

    response = client.get("/api/conversas")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [propria["id"]]


def test_aluno_nao_filtra_por_outro_aluno(sessao: Session, client: TestClient) -> None:
    _, usuario_aluno, usuario_outro = _montar_usuarios(sessao)
    _autenticar(client, usuario_aluno)

    response = client.get("/api/conversas", params={"aluno_id": str(usuario_outro.aluno_id)})

    assert response.status_code == 403


def test_admin_lista_todas_as_sessoes(sessao: Session, client: TestClient) -> None:
    admin, usuario_aluno, usuario_outro = _montar_usuarios(sessao)
    _autenticar(client, usuario_aluno)
    client.post("/api/conversas")
    _autenticar(client, usuario_outro)
    client.post("/api/conversas")

    _autenticar(client, admin)
    response = client.get("/api/conversas")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_detalhe_respeita_escopo(sessao: Session, client: TestClient) -> None:
    _, usuario_aluno, usuario_outro = _montar_usuarios(sessao)
    _autenticar(client, usuario_outro)
    conversa = client.post("/api/conversas").json()

    _autenticar(client, usuario_aluno)
    assert client.get(f"/api/conversas/{conversa['id']}").status_code == 403

    _autenticar(client, usuario_outro)
    assert client.get(f"/api/conversas/{conversa['id']}").status_code == 200


def test_job_fecha_sessao_inativa_por_timeout(
    sessao: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("THREAD_TIMEOUT_MIN", "10")
    aluno = AlunoRepository(sessao).criar(
        cpf="99988877766", nome_completo="Aluno Timeout", email="timeout@exemplo.com"
    )
    repo = ConversaRepository(sessao)
    conversa = repo.abrir(aluno.id)
    conversa.ultima_interacao = datetime.now(timezone.utc) - timedelta(minutes=11)
    sessao.commit()

    fechadas = fechar_conversas_inativas(sessao)

    assert [item.id for item in fechadas] == [conversa.id]
    assert conversa.status is StatusConversa.FECHADA
    assert conversa.motivo_fechamento is MotivoFechamento.TIMEOUT
    assert conversa.data_fim is not None


def test_job_preserva_sessao_com_interacao_recente(
    sessao: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("THREAD_TIMEOUT_MIN", "10")
    aluno = AlunoRepository(sessao).criar(
        cpf="99988877766", nome_completo="Aluno Ativo", email="ativo@exemplo.com"
    )
    conversa = ConversaRepository(sessao).abrir(aluno.id)

    assert fechar_conversas_inativas(sessao) == []
    assert conversa.status is StatusConversa.ABERTA


def test_registrar_interacao_adia_o_timeout(
    sessao: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("THREAD_TIMEOUT_MIN", "10")
    aluno = AlunoRepository(sessao).criar(
        cpf="99988877766", nome_completo="Aluno Ativo", email="ativo@exemplo.com"
    )
    repo = ConversaRepository(sessao)
    conversa = repo.abrir(aluno.id)
    conversa.ultima_interacao = datetime.now(timezone.utc) - timedelta(minutes=30)
    sessao.commit()

    repo.registrar_interacao(conversa.id)

    assert fechar_conversas_inativas(sessao) == []
    assert conversa.status is StatusConversa.ABERTA


def test_timeout_minutos_le_ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("THREAD_TIMEOUT_MIN", "25")
    assert timeout_minutos() == 25

    monkeypatch.setenv("THREAD_TIMEOUT_MIN", "invalido")
    assert timeout_minutos() == 10
