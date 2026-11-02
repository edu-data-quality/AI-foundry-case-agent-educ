"""Testes do repositório de conversas (rastreio de sessão do aluno)."""

import pytest
from sqlalchemy.orm import Session

from app.db.models import MotivoFechamento, StatusConversa
from app.repositories.alunos import AlunoRepository
from app.repositories.conversas import ConversaRepository


def _criar_aluno(sessao: Session, cpf: str = "12345678901"):
    return AlunoRepository(sessao).criar(
        cpf=cpf, nome_completo="Maria Souza", email="maria@exemplo.com"
    )


def test_abre_conversa_com_status_e_data_de_inicio(sessao: Session) -> None:
    aluno = _criar_aluno(sessao)

    conversa = ConversaRepository(sessao).abrir(aluno.id)

    assert conversa.status is StatusConversa.ABERTA
    assert conversa.data_inicio is not None
    assert conversa.data_fim is None
    assert conversa.motivo_fechamento is None


def test_registra_thread_id_do_foundry(sessao: Session) -> None:
    aluno = _criar_aluno(sessao)

    conversa = ConversaRepository(sessao).abrir(aluno.id, thread_id_foundry="thread-123")

    assert conversa.thread_id_foundry == "thread-123"


def test_fecha_conversa_com_motivo_e_data_de_fim(sessao: Session) -> None:
    aluno = _criar_aluno(sessao)
    repo = ConversaRepository(sessao)
    conversa = repo.abrir(aluno.id)

    fechada = repo.fechar(conversa.id, MotivoFechamento.LOGOUT)

    assert fechada.status is StatusConversa.FECHADA
    assert fechada.motivo_fechamento is MotivoFechamento.LOGOUT
    assert fechada.data_fim is not None
    assert fechada.data_fim.tzinfo is not None
    assert fechada.data_fim >= fechada.data_inicio


def test_conversa_fechada_nao_pode_ser_fechada_de_novo(sessao: Session) -> None:
    aluno = _criar_aluno(sessao)
    repo = ConversaRepository(sessao)
    conversa = repo.abrir(aluno.id)
    repo.fechar(conversa.id, MotivoFechamento.LOGOUT)

    with pytest.raises(ValueError, match="já está fechada"):
        repo.fechar(conversa.id, MotivoFechamento.TIMEOUT)


def test_aluno_nao_pode_ter_duas_conversas_abertas(sessao: Session) -> None:
    aluno = _criar_aluno(sessao)
    repo = ConversaRepository(sessao)
    repo.abrir(aluno.id)

    with pytest.raises(ValueError, match="já tem conversa aberta"):
        repo.abrir(aluno.id)


def test_busca_conversa_aberta_do_aluno(sessao: Session) -> None:
    aluno = _criar_aluno(sessao)
    repo = ConversaRepository(sessao)
    conversa = repo.abrir(aluno.id)

    assert repo.buscar_aberta_por_aluno(aluno.id).id == conversa.id

    repo.fechar(conversa.id, MotivoFechamento.TIMEOUT)

    assert repo.buscar_aberta_por_aluno(aluno.id) is None
