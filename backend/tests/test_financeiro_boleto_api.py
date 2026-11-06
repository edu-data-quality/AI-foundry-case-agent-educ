"""Testes do endpoint de boletos (issue #5 / PRD 5, US1.2).

Critérios de aceitação cobertos:
- aluno autenticado recebe os próprios boletos pendentes;
- campo retornado respeita o contrato (linha_digitavel, qr_code_pix,
  data_vencimento, status_pagamento);
- 403 para aluno consultando outro CPF;
- 404 para CPF inexistente (consulta ADMIN);
- contrato documentado no OpenAPI do backend.
"""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import RoleUsuario, StatusPagamento, Usuario
from app.db.session import get_db
from app.main import app
from app.repositories.alunos import AlunoRepository
from app.repositories.financeiro import MensalidadeRepository
from app.repositories.usuarios import UsuarioRepository
from app.security import hash_senha

CPF_ALUNO = "11122233344"
CPF_OUTRO_ALUNO = "55566677788"

LINHA_DIGITAVEL = "23793.38128 60007.827136 95000.063305 9 00000000045000"
QR_CODE_PIX = "00020126pix-simulado-2026-11"


def _montar_dados(sessao: Session) -> tuple[Usuario, Usuario]:
    """Cria dois alunos com boletos e usuários admin/aluno."""
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

    mensalidades = MensalidadeRepository(sessao)
    mensalidades.criar(
        aluno_id=aluno.id,
        mes_referencia="2026-11",
        valor_original=Decimal("450.00"),
        data_vencimento=date(2026, 11, 10),
        linha_digitavel=LINHA_DIGITAVEL,
        qr_code_pix=QR_CODE_PIX,
    )
    mensalidades.criar(
        aluno_id=aluno.id,
        mes_referencia="2026-09",
        valor_original=Decimal("450.00"),
        data_vencimento=date(2026, 9, 10),
        status_pagamento=StatusPagamento.ATRASADO,
        linha_digitavel="23793.38128 60007.827136 95000.063305 9 00000000045000",
        qr_code_pix="00020126pix-simulado-2026-09",
    )
    mensalidades.criar(
        aluno_id=aluno.id,
        mes_referencia="2026-10",
        valor_original=Decimal("450.00"),
        data_vencimento=date(2026, 10, 10),
        status_pagamento=StatusPagamento.PAGO,
        linha_digitavel="23793.38128 60007.827136 95000.063305 9 00000000045000",
        qr_code_pix="00020126pix-simulado-2026-10",
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


def test_aluno_consulta_proprios_boletos(sessao: Session, client: TestClient) -> None:
    _, aluno_user = _montar_dados(sessao)
    _fazer_login(client, "aluna", "aluna123")

    response = client.get("/api/financeiro/boleto", params={"cpf": CPF_ALUNO})

    assert response.status_code == 200
    boletos = response.json()
    assert len(boletos) == 2

    por_mes = {b["data_vencimento"]: b for b in boletos}
    pendente = por_mes["2026-11-10"]
    assert pendente["linha_digitavel"] == LINHA_DIGITAVEL
    assert pendente["qr_code_pix"] == QR_CODE_PIX
    assert pendente["status_pagamento"] == "PENDENTE"

    atrasado = por_mes["2026-09-10"]
    assert atrasado["status_pagamento"] == "ATRASADO"


def test_boleto_nao_inclui_boletos_pagos(
    sessao: Session, client: TestClient
) -> None:
    _montar_dados(sessao)
    _fazer_login(client, "aluna", "aluna123")

    response = client.get("/api/financeiro/boleto", params={"cpf": CPF_ALUNO})

    assert response.status_code == 200
    vencimentos = {b["data_vencimento"] for b in response.json()}
    assert "2026-10-10" not in vencimentos


def test_aluno_consultando_outro_cpf_retorna_403(
    sessao: Session, client: TestClient
) -> None:
    _montar_dados(sessao)
    _fazer_login(client, "aluna", "aluna123")

    response = client.get("/api/financeiro/boleto", params={"cpf": CPF_OUTRO_ALUNO})

    assert response.status_code == 403
    assert response.json()["detail"] == "acesso restrito aos próprios dados"


def test_aluno_consultando_cpf_inexistente_retorna_403(
    sessao: Session, client: TestClient
) -> None:
    """ALUNO nunca recebe 404: CPF desconhecido também é 403 (sem enumeração)."""
    _montar_dados(sessao)
    _fazer_login(client, "aluna", "aluna123")

    response = client.get("/api/financeiro/boleto", params={"cpf": "99999999999"})

    assert response.status_code == 403
    assert response.json()["detail"] == "acesso restrito aos próprios dados"


def test_admin_consulta_boletos_de_qualquer_aluno(
    sessao: Session, client: TestClient
) -> None:
    _montar_dados(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.get("/api/financeiro/boleto", params={"cpf": CPF_ALUNO})

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_cpf_inexistente_retorna_404(sessao: Session, client: TestClient) -> None:
    _montar_dados(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.get("/api/financeiro/boleto", params={"cpf": "99999999999"})

    assert response.status_code == 404
    assert response.json()["detail"] == "aluno não encontrado"


def test_sem_token_retorna_401(sessao: Session, client: TestClient) -> None:
    _montar_dados(sessao)

    response = client.get("/api/financeiro/boleto", params={"cpf": CPF_ALUNO})

    assert response.status_code == 401


def test_cpf_invalido_retorna_422(sessao: Session, client: TestClient) -> None:
    _montar_dados(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.get("/api/financeiro/boleto", params={"cpf": "123"})

    assert response.status_code == 422


def test_aluno_sem_boletos_em_aberto_retorna_lista_vazia(
    sessao: Session, client: TestClient
) -> None:
    _montar_dados(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.get("/api/financeiro/boleto", params={"cpf": CPF_OUTRO_ALUNO})

    assert response.status_code == 200
    assert response.json() == []


def test_endpoint_documentado_no_openapi() -> None:
    """O contrato do endpoint aparece no OpenAPI do próprio backend."""
    operacao = app.openapi()["paths"]["/api/financeiro/boleto"]["get"]

    assert operacao["tags"] == ["financeiro"]
    parametros = {p["name"]: p for p in operacao["parameters"]}
    assert parametros["cpf"]["required"] is True
    assert parametros["cpf"]["schema"]["pattern"] == r"^\d{11}$"
    assert "200" in operacao["responses"]
    assert "403" in operacao["responses"]
    assert "404" in operacao["responses"]
    assert "422" in operacao["responses"]