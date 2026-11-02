"""Integração: repositórios e seed rodando sobre o schema da migração."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import seed
from app.db.models import Aluno, Mensalidade, StatusPagamento
from app.repositories.alunos import AlunoRepository
from app.repositories.conversas import ConversaRepository
from app.repositories.financeiro import MensalidadeRepository
from app.repositories.usuarios import UsuarioRepository


def test_seed_roda_sobre_schema_migrado(sessao_migrada: Session) -> None:
    resumo = seed.executar(sessao_migrada)

    assert resumo["alunos"] == 1
    assert resumo["usuarios"] == 2
    assert UsuarioRepository(sessao_migrada).buscar_por_login(seed.LOGIN_ADMIN) is not None


def test_repositorios_leem_dados_do_seed(sessao_migrada: Session) -> None:
    seed.executar(sessao_migrada)

    aluno = sessao_migrada.scalar(select(Aluno).where(Aluno.cpf == seed.CPF_ALUNO_DEMO))
    em_aberto = MensalidadeRepository(sessao_migrada).listar_em_aberto_por_aluno(aluno.id)
    todas = MensalidadeRepository(sessao_migrada).listar_por_aluno(aluno.id)

    assert len(todas) == 2
    assert [mensalidade.mes_referencia for mensalidade in em_aberto] == ["2026-11"]
    assert em_aberto[0].status_pagamento is StatusPagamento.PENDENTE
    assert sessao_migrada.scalar(select(Mensalidade).where(Mensalidade.id == todas[0].id))


def test_conversa_aberta_sobre_schema_migrado(sessao_migrada: Session) -> None:
    seed.executar(sessao_migrada)
    aluno = sessao_migrada.scalar(select(Aluno).where(Aluno.cpf == seed.CPF_ALUNO_DEMO))
    repo = ConversaRepository(sessao_migrada)

    conversa = repo.abrir(aluno.id, thread_id_foundry="thread-migrada")

    assert repo.buscar_aberta_por_aluno(aluno.id).id == conversa.id


def test_aluno_repository_sobre_schema_migrado(sessao_migrada: Session) -> None:
    repo = AlunoRepository(sessao_migrada)
    criado = repo.criar(
        cpf="98765432100", nome_completo="Teste Migração", email="teste@exemplo.com"
    )

    assert repo.buscar_por_cpf("98765432100").id == criado.id
