"""Testes da emissão de declaração de matrícula (issue #6 / PRD 5, US1.2).

Critérios de aceitação cobertos:
- aluno autenticado emite apenas a própria declaração;
- PDF gerado a partir do template HTML e anexado ao e-mail;
- envio pelo Resend real (payload/headers) e modo simulado sem chave;
- registro de auditoria em `solicitacoes_documentos`;
- erros: 403 (outro aluno), 404 (id inexistente), 422 (payload/e-mail), 502
  (falha do provedor) sem registrar solicitação;
- contrato documentado no OpenAPI do backend.
"""

import base64
import uuid
from datetime import date

import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import declaracoes as modulo_declaracoes
from app.api.routes import declaracoes as rotas_declaracoes
from app.db.models import RoleUsuario, Usuario
from app.db.session import get_db
from app.declaracoes import (
    DadosDeclaracao,
    ErroEnvioEmail,
    enviar_email_declaracao,
    gerar_pdf_matricula,
)
from app.main import app
from app.repositories.alunos import AlunoRepository
from app.repositories.documentos import SolicitacaoDocumentoRepository
from app.repositories.usuarios import UsuarioRepository
from app.security import hash_senha

CPF_ALUNO = "11122233344"
CPF_OUTRO_ALUNO = "55566677788"

DADOS = DadosDeclaracao(
    nome_completo="Aluna Teste",
    cpf=CPF_ALUNO,
    email="aluna@exemplo.com",
    curso="Análise e Desenvolvimento de Sistemas",
    polo="São Paulo",
)


def _montar_dados(sessao: Session) -> tuple[Usuario, Usuario]:
    """Cria dois alunos e os usuários admin/aluno do teste."""
    alunos = AlunoRepository(sessao)
    aluno = alunos.criar(
        cpf=CPF_ALUNO,
        nome_completo="Aluna Teste",
        email="aluna@exemplo.com",
        curso="Análise e Desenvolvimento de Sistemas",
        polo="São Paulo",
    )
    alunos.criar(
        cpf=CPF_OUTRO_ALUNO,
        nome_completo="Outro Aluno",
        email="outro@exemplo.com",
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


@pytest.fixture()
def envios(monkeypatch: pytest.MonkeyPatch) -> list[tuple[DadosDeclaracao, bytes]]:
    """Substitui o envio real por um fake que captura dados e PDF."""
    capturados: list[tuple[DadosDeclaracao, bytes]] = []

    def falso(dados: DadosDeclaracao, pdf: bytes) -> bool:
        capturados.append((dados, pdf))
        return True

    monkeypatch.setattr(rotas_declaracoes, "enviar_email_declaracao", falso)
    return capturados


def _fazer_login(client: TestClient, login: str, senha: str) -> None:
    """Autentica e anexa o header Bearer ao client."""
    response = client.post("/api/auth/login", json={"login": login, "senha": senha})
    assert response.status_code == 200
    client.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})


def _aluno_id(sessao: Session, cpf: str = CPF_ALUNO) -> str:
    aluno = AlunoRepository(sessao).buscar_por_cpf(cpf)
    assert aluno is not None
    return str(aluno.id)


def test_aluno_emite_propria_declaracao(
    sessao: Session, client: TestClient, envios: list[tuple[DadosDeclaracao, bytes]]
) -> None:
    _montar_dados(sessao)
    _fazer_login(client, "aluna", "aluna123")

    response = client.post(
        "/api/declaracoes/gerar",
        json={"aluno_id": _aluno_id(sessao), "tipo": "matricula"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "sucesso",
        "email_destino": "aluna@exemplo.com",
    }
    assert len(envios) == 1
    dados, pdf = envios[0]
    assert dados.nome_completo == "Aluna Teste"
    assert dados.email == "aluna@exemplo.com"
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000

    solicitacoes = SolicitacaoDocumentoRepository(sessao).listar_por_aluno(
        uuid.UUID(_aluno_id(sessao))
    )
    assert len(solicitacoes) == 1
    assert solicitacoes[0].tipo_documento == "matricula"
    assert solicitacoes[0].enviado_para_email == "aluna@exemplo.com"


def test_aluno_nao_emite_para_outro_aluno(
    sessao: Session, client: TestClient, envios: list[tuple[DadosDeclaracao, bytes]]
) -> None:
    _montar_dados(sessao)
    _fazer_login(client, "aluna", "aluna123")

    response = client.post(
        "/api/declaracoes/gerar",
        json={"aluno_id": _aluno_id(sessao, CPF_OUTRO_ALUNO), "tipo": "matricula"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "acesso restrito aos próprios dados"
    assert envios == []
    assert SolicitacaoDocumentoRepository(sessao).listar_por_aluno(
        uuid.UUID(_aluno_id(sessao))
    ) == []


def test_aluno_com_id_inexistente_retorna_403(
    sessao: Session, client: TestClient, envios: list[tuple[DadosDeclaracao, bytes]]
) -> None:
    """ALUNO nunca recebe 404: id desconhecido também é 403 (sem enumeração)."""
    _montar_dados(sessao)
    _fazer_login(client, "aluna", "aluna123")

    response = client.post(
        "/api/declaracoes/gerar",
        json={"aluno_id": str(uuid.uuid4()), "tipo": "matricula"},
    )

    assert response.status_code == 403
    assert envios == []


def test_admin_emite_para_qualquer_aluno(
    sessao: Session, client: TestClient, envios: list[tuple[DadosDeclaracao, bytes]]
) -> None:
    _montar_dados(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.post(
        "/api/declaracoes/gerar",
        json={"aluno_id": _aluno_id(sessao, CPF_OUTRO_ALUNO), "tipo": "matricula"},
    )

    assert response.status_code == 200
    assert response.json()["email_destino"] == "outro@exemplo.com"
    assert len(envios) == 1


def test_admin_com_aluno_inexistente_retorna_404(
    sessao: Session, client: TestClient, envios: list[tuple[DadosDeclaracao, bytes]]
) -> None:
    _montar_dados(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.post(
        "/api/declaracoes/gerar",
        json={"aluno_id": str(uuid.uuid4()), "tipo": "matricula"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "aluno não encontrado"
    assert envios == []


def test_sem_token_retorna_401(
    sessao: Session, envios: list[tuple[DadosDeclaracao, bytes]]
) -> None:
    _montar_dados(sessao)
    app.dependency_overrides[get_db] = lambda: sessao
    try:
        response = TestClient(app).post(
            "/api/declaracoes/gerar",
            json={"aluno_id": _aluno_id(sessao), "tipo": "matricula"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert envios == []


def test_tipo_desconhecido_retorna_422(
    sessao: Session, client: TestClient, envios: list[tuple[DadosDeclaracao, bytes]]
) -> None:
    _montar_dados(sessao)
    _fazer_login(client, "aluna", "aluna123")

    response = client.post(
        "/api/declaracoes/gerar",
        json={"aluno_id": _aluno_id(sessao), "tipo": "historico"},
    )

    assert response.status_code == 422
    assert envios == []


def test_email_invalido_retorna_422_sem_gerar_pdf(
    sessao: Session, client: TestClient, envios: list[tuple[DadosDeclaracao, bytes]]
) -> None:
    alunos = AlunoRepository(sessao)
    aluno = alunos.criar(
        cpf="99988877766",
        nome_completo="Aluno Sem Email",
        email="sem-arroba",
    )
    _montar_dados(sessao)
    _fazer_login(client, "admin", "admin123")

    response = client.post(
        "/api/declaracoes/gerar",
        json={"aluno_id": str(aluno.id), "tipo": "matricula"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "e-mail do aluno inválido"
    assert envios == []


def test_falha_do_provedor_retorna_502_e_nao_registra(
    sessao: Session, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _montar_dados(sessao)
    _fazer_login(client, "aluna", "aluna123")

    def falha(dados: DadosDeclaracao, pdf: bytes) -> bool:
        raise ErroEnvioEmail("Resend respondeu 500: indisponível")

    monkeypatch.setattr(rotas_declaracoes, "enviar_email_declaracao", falha)

    response = client.post(
        "/api/declaracoes/gerar",
        json={"aluno_id": _aluno_id(sessao), "tipo": "matricula"},
    )

    assert response.status_code == 502
    assert "falha ao enviar e-mail" in response.json()["detail"]
    assert SolicitacaoDocumentoRepository(sessao).listar_por_aluno(
        uuid.UUID(_aluno_id(sessao))
    ) == []


def test_sem_chave_resend_responde_simulado(
    sessao: Session,
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Modo dev: PDF + registro acontecem, mas o status não finge envio real."""
    _montar_dados(sessao)
    _fazer_login(client, "aluna", "aluna123")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    with caplog.at_level("WARNING", logger="app.declaracoes"):
        response = client.post(
            "/api/declaracoes/gerar",
            json={"aluno_id": _aluno_id(sessao), "tipo": "matricula"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "simulado"
    assert "SIMULADO" in caplog.text
    assert len(
        SolicitacaoDocumentoRepository(sessao).listar_por_aluno(
            uuid.UUID(_aluno_id(sessao))
        )
    ) == 1


def test_pdf_e_gerado_do_template_html() -> None:
    pdf = gerar_pdf_matricula(DADOS, data=date(2026, 11, 14))

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_email_real_envia_anexo_e_autorizacao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Contrato com o Resend: endpoint, Bearer, destinatário e PDF em base64."""
    monkeypatch.setenv("RESEND_API_KEY", "re_chave_teste")
    monkeypatch.setenv("RESEND_FROM", "EAD <nao-responda@exemplo.com>")
    pdf = gerar_pdf_matricula(DADOS, data=date(2026, 11, 14))
    capturado: dict = {}

    class RespostaFalsa:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

    def post_falso(url: str, **kwargs) -> RespostaFalsa:
        capturado["url"] = url
        capturado.update(kwargs)
        return RespostaFalsa()

    monkeypatch.setattr(modulo_declaracoes.requests, "post", post_falso)

    enviado = enviar_email_declaracao(DADOS, pdf, data=date(2026, 11, 14))

    assert enviado is True
    assert capturado["url"] == "https://api.resend.com/emails"
    assert capturado["headers"]["Authorization"] == "Bearer re_chave_teste"
    assert capturado["json"]["to"] == ["aluna@exemplo.com"]
    assert capturado["json"]["from"] == "EAD <nao-responda@exemplo.com>"
    anexo = capturado["json"]["attachments"][0]
    assert anexo["filename"] == "declaracao-matricula.pdf"
    assert base64.b64decode(anexo["content"]).startswith(b"%PDF")


def test_email_real_sem_chave_simula_sem_chamar_resend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    def post_que_nao_deveria_ser_chamado(*args, **kwargs):
        raise AssertionError("Resend não deve ser chamado sem chave")

    monkeypatch.setattr(modulo_declaracoes.requests, "post", post_que_nao_deveria_ser_chamado)

    assert enviar_email_declaracao(DADOS, b"%PDF-1.4 fake") is False


def test_falha_de_rede_levanta_erro_envio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "re_chave_teste")

    def post_com_erro(*args, **kwargs):
        raise requests.ConnectionError("sem rota para api.resend.com")

    monkeypatch.setattr(modulo_declaracoes.requests, "post", post_com_erro)

    with pytest.raises(ErroEnvioEmail, match="falha de comunicação"):
        enviar_email_declaracao(DADOS, b"%PDF-1.4 fake")


def test_endpoint_documentado_no_openapi() -> None:
    """O contrato do endpoint aparece no OpenAPI do próprio backend."""
    operacao = app.openapi()["paths"]["/api/declaracoes/gerar"]["post"]

    assert operacao["tags"] == ["declaracoes"]
    assert "requestBody" in operacao
    assert "200" in operacao["responses"]
    assert "403" in operacao["responses"]
    assert "404" in operacao["responses"]
    assert "422" in operacao["responses"]
    assert "502" in operacao["responses"]
