"""Testes dos endpoints administrativos (issue #7 / PRD 5, US1.3 e US4.2).

Cobertura dos critérios de aceitação:
- ADMIN cadastra aluno e altera notas, boleto e matrícula em runtime;
- mudança refletida imediatamente nas consultas (S4/S5);
- aluno comum recebe 403 em todos os endpoints admin;
- 401 sem token; 404 para recurso inexistente;
- contratos documentados no OpenAPI.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import (
    RoleUsuario,
    StatusDisciplina,
    StatusMatricula,
    StatusPagamento,
    Usuario,
)
from app.db.session import get_db
from app.main import app
from app.repositories.academico import DisciplinaRepository, MatriculaRepository
from app.repositories.alunos import AlunoRepository
from app.repositories.financeiro import MensalidadeRepository
from app.repositories.usuarios import UsuarioRepository
from app.security import hash_senha

CPF_ALUNO = "11122233344"
CPF_NOVO = "99988877766"


@pytest.fixture()
def client(sessao: Session) -> TestClient:
    """Client do app real com a sessão de teste injetada."""
    app.dependency_overrides[get_db] = lambda: sessao
    yield TestClient(app)
    app.dependency_overrides.clear()


def _montar_ambiente(sessao: Session) -> tuple[Usuario, uuid.UUID, uuid.UUID, uuid.UUID]:
    """Cria admin, aluno, matrícula e mensalidade; retorna (admin, aluno_id,
    matricula_id, mensalidade_id)."""
    alunos = AlunoRepository(sessao)
    admin = UsuarioRepository(sessao).criar(
        login="admin", senha_hash=hash_senha("admin123"), role=RoleUsuario.ADMIN
    )

    aluno = alunos.criar(
        cpf=CPF_ALUNO,
        nome_completo="Aluna Teste",
        email="aluna@exemplo.com",
        curso="ADS",
        polo="São Paulo",
    )
    UsuarioRepository(sessao).criar(
        login="aluna",
        senha_hash=hash_senha("aluna123"),
        role=RoleUsuario.ALUNO,
        aluno_id=aluno.id,
    )

    disciplina = DisciplinaRepository(sessao).criar(
        codigo="ADS101", nome="Algoritmos", semestre_ideal=1
    )
    matricula = MatriculaRepository(sessao).criar(
        aluno_id=aluno.id,
        disciplina_id=disciplina.id,
        semestre_letivo="2026.1",
        status_disciplina=StatusDisciplina.AGUARDANDO_NOTA,
    )

    mensalidade = MensalidadeRepository(sessao).criar(
        aluno_id=aluno.id,
        mes_referencia="2026-11",
        valor_original=Decimal("450.00"),
        data_vencimento=date(2026, 11, 10),
        status_pagamento=StatusPagamento.PENDENTE,
    )

    return admin, aluno.id, matricula.id, mensalidade.id


def _fazer_login(client: TestClient, login: str, senha: str) -> None:
    """Autentica e anexa o header Bearer ao client."""
    response = client.post("/api/auth/login", json={"login": login, "senha": senha})
    assert response.status_code == 200
    client.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})


# ---------------------------------------------------------------------------
# POST /api/admin/alunos
# ---------------------------------------------------------------------------


def test_admin_cria_aluno(sessao: Session, client: TestClient) -> None:
    _montar_ambiente(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.post(
        "/api/admin/alunos",
        json={
            "cpf": CPF_NOVO,
            "nome_completo": "Novo Aluno Fictício",
            "email": "novo@exemplo.com",
            "telefone": "11999990000",
            "curso": "ADS",
            "polo": "Rio de Janeiro",
        },
    )

    assert response.status_code == 201
    corpo = response.json()
    assert corpo["cpf"] == CPF_NOVO
    assert corpo["nome_completo"] == "Novo Aluno Fictício"
    assert corpo["status_matricula"] == "ATIVO"

    # Persistido e consultável de imediato (S4/S5)
    status = client.get("/api/aluno/status", params={"cpf": CPF_NOVO})
    assert status.status_code == 200
    assert status.json()["aluno"]["nome_completo"] == "Novo Aluno Fictício"


def test_admin_criar_aluno_cpf_duplicado_retorna_409(
    sessao: Session, client: TestClient
) -> None:
    _montar_ambiente(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.post(
        "/api/admin/alunos",
        json={"cpf": CPF_ALUNO, "nome_completo": "Dup", "email": "dup@exemplo.com"},
    )

    assert response.status_code == 409


def test_admin_criar_aluno_dados_invalidos_retorna_422(
    sessao: Session, client: TestClient
) -> None:
    _montar_ambiente(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.post(
        "/api/admin/alunos",
        json={"cpf": "123", "nome_completo": "", "email": "nao-email"},
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# PATCH notas
# ---------------------------------------------------------------------------


def test_admin_lanca_notas_e_muda_status_disciplina(
    sessao: Session, client: TestClient
) -> None:
    _, aluno_id, matricula_id, _ = _montar_ambiente(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.patch(
        f"/api/admin/alunos/{aluno_id}/matriculas/{matricula_id}/notas",
        json={"nota_av1": 8.0, "nota_av2": 9.0, "nota_final": 8.5,
              "status_disciplina": "APROVADO"},
    )

    assert response.status_code == 200
    corpo = response.json()
    assert corpo["nota_av1"] == 8.0
    assert corpo["status_disciplina"] == "APROVADO"

    # Refletido na consulta do aluno (S4/S5)
    status = client.get("/api/aluno/status", params={"cpf": CPF_ALUNO})
    disciplina = status.json()["disciplinas"][0]
    assert disciplina["nota_av1"] == 8.0
    assert disciplina["status_disciplina"] == "APROVADO"


def test_notas_matricula_de_outro_aluno_retorna_404(
    sessao: Session, client: TestClient
) -> None:
    _, aluno_id, _, _ = _montar_ambiente(sessao)
    _fazer_login(client, "admin", "admin123")
    matricula_alheia = uuid.uuid4()

    response = client.patch(
        f"/api/admin/alunos/{aluno_id}/matriculas/{matricula_alheia}/notas",
        json={"nota_av1": 7.0, "nota_av2": 7.0, "nota_final": 7.0,
              "status_disciplina": "APROVADO"},
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH mensalidade status
# ---------------------------------------------------------------------------


def test_admin_alterar_status_mensalidade(
    sessao: Session, client: TestClient
) -> None:
    _, _, _, mensalidade_id = _montar_ambiente(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.patch(
        f"/api/admin/mensalidades/{mensalidade_id}/status",
        json={"status": "PAGO"},
    )

    assert response.status_code == 200
    assert response.json()["status_pagamento"] == "PAGO"

    # Refletido imediatamente na consulta de boleto (S4/S5)
    boleto = client.get("/api/financeiro/boleto", params={"cpf": CPF_ALUNO})
    assert boleto.status_code == 200
    assert boleto.json() == []  # nenhum em aberto


def test_admin_mensalidade_inexistente_retorna_404(
    sessao: Session, client: TestClient
) -> None:
    _montar_ambiente(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.patch(
        f"/api/admin/mensalidades/{uuid.uuid4()}/status",
        json={"status": "ATRASADO"},
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH matrícula status
# ---------------------------------------------------------------------------


def test_admin_alterar_status_matricula(
    sessao: Session, client: TestClient
) -> None:
    _, aluno_id, _, _ = _montar_ambiente(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.patch(
        f"/api/admin/alunos/{aluno_id}/matricula-status",
        json={"status": "TRANCADO"},
    )

    assert response.status_code == 200
    assert response.json()["status_matricula"] == "TRANCADO"

    status = client.get("/api/aluno/status", params={"cpf": CPF_ALUNO})
    assert status.json()["aluno"]["status_matricula"] == "TRANCADO"


def test_admin_aluno_inexistente_retorna_404(
    sessao: Session, client: TestClient
) -> None:
    _montar_ambiente(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.patch(
        f"/api/admin/alunos/{uuid.uuid4()}/matricula-status",
        json={"status": "CONCLUIDO"},
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Autorização e documentação
# ---------------------------------------------------------------------------


def test_aluno_comum_recebe_403_em_todos_os_endpoints_admin(
    sessao: Session, client: TestClient
) -> None:
    _, aluno_id, matricula_id, mensalidade_id = _montar_ambiente(sessao)
    _fazer_login(client, "aluna", "aluna123")

    assert client.post("/api/admin/alunos", json={
        "cpf": CPF_NOVO, "nome_completo": "X", "email": "x@x.com"}).status_code == 403
    assert client.patch(
        f"/api/admin/alunos/{aluno_id}/matriculas/{matricula_id}/notas",
        json={"nota_av1": 1.0, "nota_av2": 1.0, "nota_final": 1.0,
              "status_disciplina": "REPROVADO"},
    ).status_code == 403
    assert client.patch(
        f"/api/admin/mensalidades/{mensalidade_id}/status",
        json={"status": "PAGO"},
    ).status_code == 403
    assert client.patch(
        f"/api/admin/alunos/{aluno_id}/matricula-status",
        json={"status": "TRANCADO"},
    ).status_code == 403


def test_sem_token_recebe_401(sessao: Session, client: TestClient) -> None:
    _montar_ambiente(sessao)

    assert client.post("/api/admin/alunos", json={
        "cpf": CPF_NOVO, "nome_completo": "X", "email": "x@x.com"}).status_code == 401


def test_endpoints_admin_documentados_no_openapi() -> None:
    """Os contratos admin aparecem no OpenAPI do próprio backend."""
    pe = app.openapi()["paths"]
    assert "/api/admin/alunos" in pe
    assert "/api/admin/alunos/{aluno_id}" in pe
    assert "/api/admin/alunos/{aluno_id}/matriculas/{matricula_id}/notas" in pe
    assert "/api/admin/mensalidades/{mensalidade_id}/status" in pe
    assert "/api/admin/alunos/{aluno_id}/matricula-status" in pe


def test_status_matricula_invalido_retorna_422(
    sessao: Session, client: TestClient
) -> None:
    _, aluno_id, _, _ = _montar_ambiente(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.patch(
        f"/api/admin/alunos/{aluno_id}/matricula-status",
        json={"status": "INEXISTENTE"},
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/admin/alunos (listagem + busca) — issue #16
# ---------------------------------------------------------------------------


def _criar_segundo_aluno(sessao: Session):
    """Cria um aluno adicional para exercitar listagem e busca."""
    return AlunoRepository(sessao).criar(
        cpf=CPF_NOVO,
        nome_completo="Bruno Souza",
        email="bruno@exemplo.com",
        curso="ADS",
        polo="Recife",
    )


def test_admin_lista_alunos_ordenado_por_nome(
    sessao: Session, client: TestClient
) -> None:
    _montar_ambiente(sessao)
    _criar_segundo_aluno(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.get("/api/admin/alunos")

    assert response.status_code == 200
    corpo = response.json()
    assert [aluno["nome_completo"] for aluno in corpo] == ["Aluna Teste", "Bruno Souza"]
    assert corpo[0]["cpf"] == CPF_ALUNO
    assert corpo[0]["curso"] == "ADS"
    assert corpo[0]["polo"] == "São Paulo"
    assert corpo[0]["status_matricula"] == "ATIVO"


def test_admin_busca_aluno_por_nome_parcial_sem_case(
    sessao: Session, client: TestClient
) -> None:
    _montar_ambiente(sessao)
    _criar_segundo_aluno(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.get("/api/admin/alunos", params={"busca": "bruNO"})

    assert response.status_code == 200
    corpo = response.json()
    assert [aluno["nome_completo"] for aluno in corpo] == ["Bruno Souza"]


def test_admin_busca_aluno_por_prefixo_de_cpf(
    sessao: Session, client: TestClient
) -> None:
    _montar_ambiente(sessao)
    _criar_segundo_aluno(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.get("/api/admin/alunos", params={"busca": "999"})

    assert response.status_code == 200
    corpo = response.json()
    assert [aluno["cpf"] for aluno in corpo] == [CPF_NOVO]


def test_admin_busca_sem_resultado_retorna_lista_vazia(
    sessao: Session, client: TestClient
) -> None:
    _montar_ambiente(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.get("/api/admin/alunos", params={"busca": "inexistente"})

    assert response.status_code == 200
    assert response.json() == []


def test_aluno_comum_recebe_403_na_listagem_e_no_detalhe(
    sessao: Session, client: TestClient
) -> None:
    _, aluno_id, _, _ = _montar_ambiente(sessao)
    _fazer_login(client, "aluna", "aluna123")

    assert client.get("/api/admin/alunos").status_code == 403
    assert client.get(f"/api/admin/alunos/{aluno_id}").status_code == 403


def test_listagem_sem_token_recebe_401(sessao: Session, client: TestClient) -> None:
    _montar_ambiente(sessao)

    assert client.get("/api/admin/alunos").status_code == 401


# ---------------------------------------------------------------------------
# GET /api/admin/alunos/{aluno_id} (detalhe) — issue #16
# ---------------------------------------------------------------------------


def test_admin_detalha_aluno_com_disciplinas_e_mensalidades(
    sessao: Session, client: TestClient
) -> None:
    _, aluno_id, _, _ = _montar_ambiente(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.get(f"/api/admin/alunos/{aluno_id}")

    assert response.status_code == 200
    corpo = response.json()
    assert corpo["aluno"]["id"] == str(aluno_id)
    assert corpo["aluno"]["nome_completo"] == "Aluna Teste"

    assert len(corpo["disciplinas"]) == 1
    disciplina = corpo["disciplinas"][0]
    assert disciplina["codigo"] == "ADS101"
    assert disciplina["nome"] == "Algoritmos"
    assert disciplina["semestre_letivo"] == "2026.1"
    assert disciplina["status_disciplina"] == "AGUARDANDO_NOTA"

    assert len(corpo["mensalidades"]) == 1
    mensalidade = corpo["mensalidades"][0]
    assert mensalidade["mes_referencia"] == "2026-11"
    assert mensalidade["valor_original"] == 450.0
    assert mensalidade["data_vencimento"] == "2026-11-10"
    assert mensalidade["status_pagamento"] == "PENDENTE"


def test_detalhe_aluno_inexistente_retorna_404(
    sessao: Session, client: TestClient
) -> None:
    _montar_ambiente(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.get(f"/api/admin/alunos/{uuid.uuid4()}")

    assert response.status_code == 404