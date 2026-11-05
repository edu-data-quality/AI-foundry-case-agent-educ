"""Testes do status acadêmico do aluno (issue #4 / US1.2).

Critérios de aceitação cobertos:
- aluno autenticado recebe as próprias notas;
- 403 para aluno consultando outro CPF;
- 404 para CPF inexistente (consulta ADMIN);
- contrato documentado no OpenAPI do backend.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import RoleUsuario, StatusDisciplina, Usuario
from app.db.session import get_db
from app.main import app
from app.repositories.academico import DisciplinaRepository, MatriculaRepository
from app.repositories.alunos import AlunoRepository
from app.repositories.usuarios import UsuarioRepository
from app.security import hash_senha

CPF_ALUNO = "11122233344"
CPF_OUTRO_ALUNO = "55566677788"


def _montar_dados(sessao: Session) -> tuple[Usuario, Usuario]:
    """Cria aluno com notas, segundo aluno e usuários admin/aluno."""
    alunos = AlunoRepository(sessao)
    aluno = alunos.criar(
        cpf=CPF_ALUNO,
        nome_completo="Aluna Teste",
        email="aluna@exemplo.com",
        curso="ADS",
        polo="São Paulo",
    )
    alunos.criar(
        cpf=CPF_OUTRO_ALUNO,
        nome_completo="Outro Aluno",
        email="outro@exemplo.com",
    )

    disciplinas = DisciplinaRepository(sessao)
    aprovada = disciplinas.criar(
        codigo="ADS101", nome="Algoritmos", semestre_ideal=1
    )
    sem_nota = disciplinas.criar(
        codigo="ADS102", nome="Banco de Dados", semestre_ideal=2
    )

    matriculas = MatriculaRepository(sessao)
    matriculas.criar(
        aluno_id=aluno.id,
        disciplina_id=aprovada.id,
        semestre_letivo="2026.1",
        nota_av1=8.0,
        nota_av2=9.0,
        nota_final=8.5,
        status_disciplina=StatusDisciplina.APROVADO,
    )
    matriculas.criar(
        aluno_id=aluno.id,
        disciplina_id=sem_nota.id,
        semestre_letivo="2026.1",
        status_disciplina=StatusDisciplina.AGUARDANDO_NOTA,
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
    """Client do app real com a sessão de teste injetada."""
    app.dependency_overrides[get_db] = lambda: sessao
    yield TestClient(app)
    app.dependency_overrides.clear()


def _fazer_login(client: TestClient, login: str, senha: str) -> None:
    """Autentica e anexa o header Bearer ao client."""
    response = client.post("/api/auth/login", json={"login": login, "senha": senha})
    assert response.status_code == 200
    client.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})


def test_aluno_consulta_proprio_status(sessao: Session, client: TestClient) -> None:
    _, aluno_user = _montar_dados(sessao)
    _fazer_login(client, "aluna", "aluna123")

    response = client.get("/api/aluno/status", params={"cpf": CPF_ALUNO})

    assert response.status_code == 200
    corpo = response.json()
    assert corpo["aluno"]["id"] == str(aluno_user.aluno_id)
    assert corpo["aluno"]["cpf"] == CPF_ALUNO
    assert corpo["aluno"]["nome_completo"] == "Aluna Teste"
    assert corpo["aluno"]["status_matricula"] == "ATIVO"

    disciplinas = {d["codigo"]: d for d in corpo["disciplinas"]}
    assert set(disciplinas) == {"ADS101", "ADS102"}
    assert disciplinas["ADS101"]["nota_av1"] == 8.0
    assert disciplinas["ADS101"]["nota_av2"] == 9.0
    assert disciplinas["ADS101"]["nota_final"] == 8.5
    assert disciplinas["ADS101"]["status_disciplina"] == "APROVADO"
    assert disciplinas["ADS102"]["nota_av1"] is None
    assert disciplinas["ADS102"]["status_disciplina"] == "AGUARDANDO_NOTA"


def test_aluno_consultando_outro_cpf_retorna_403(
    sessao: Session, client: TestClient
) -> None:
    _montar_dados(sessao)
    _fazer_login(client, "aluna", "aluna123")

    response = client.get("/api/aluno/status", params={"cpf": CPF_OUTRO_ALUNO})

    assert response.status_code == 403
    assert response.json()["detail"] == "acesso restrito aos próprios dados"


def test_aluno_sem_vinculo_retorna_403(sessao: Session, client: TestClient) -> None:
    _montar_dados(sessao)
    UsuarioRepository(sessao).criar(
        login="semsala",
        senha_hash=hash_senha("senha123"),
        role=RoleUsuario.ALUNO,
    )
    _fazer_login(client, "semsala", "senha123")

    response = client.get("/api/aluno/status", params={"cpf": CPF_ALUNO})

    assert response.status_code == 403


def test_admin_consulta_status_de_qualquer_aluno(
    sessao: Session, client: TestClient
) -> None:
    _montar_dados(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.get("/api/aluno/status", params={"cpf": CPF_ALUNO})

    assert response.status_code == 200
    assert response.json()["aluno"]["cpf"] == CPF_ALUNO
    assert len(response.json()["disciplinas"]) == 2


def test_aluno_consultando_cpf_inexistente_retorna_403(
    sessao: Session, client: TestClient
) -> None:
    """ALUNO nunca recebe 404: CPF desconhecido também é 403 (sem enumeração)."""
    _montar_dados(sessao)
    _fazer_login(client, "aluna", "aluna123")

    response = client.get("/api/aluno/status", params={"cpf": "99999999999"})

    assert response.status_code == 403
    assert response.json()["detail"] == "acesso restrito aos próprios dados"


def test_cpf_inexistente_retorna_404(sessao: Session, client: TestClient) -> None:
    _montar_dados(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.get("/api/aluno/status", params={"cpf": "99999999999"})

    assert response.status_code == 404
    assert response.json()["detail"] == "aluno não encontrado"


def test_sem_token_retorna_401(sessao: Session, client: TestClient) -> None:
    _montar_dados(sessao)

    response = client.get("/api/aluno/status", params={"cpf": CPF_ALUNO})

    assert response.status_code == 401


def test_cpf_invalido_retorna_422(sessao: Session, client: TestClient) -> None:
    _montar_dados(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.get("/api/aluno/status", params={"cpf": "123"})

    assert response.status_code == 422


def test_aluno_sem_disciplinas_retorna_lista_vazia(
    sessao: Session, client: TestClient
) -> None:
    _montar_dados(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.get("/api/aluno/status", params={"cpf": CPF_OUTRO_ALUNO})

    assert response.status_code == 200
    assert response.json()["disciplinas"] == []


def test_endpoint_documentado_no_openapi() -> None:
    """O contrato do endpoint aparece no OpenAPI do próprio backend."""
    operacao = app.openapi()["paths"]["/api/aluno/status"]["get"]

    assert operacao["tags"] == ["aluno"]
    parametros = {p["name"]: p for p in operacao["parameters"]}
    assert parametros["cpf"]["required"] is True
    assert parametros["cpf"]["schema"]["pattern"] == r"^\d{11}$"
    assert "200" in operacao["responses"]
    assert "403" in operacao["responses"]
    assert "404" in operacao["responses"]
    assert "422" in operacao["responses"]
