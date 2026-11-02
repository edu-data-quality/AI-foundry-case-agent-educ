"""Testes do seed de demonstração."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import seed
from app.db.models import (
    Aluno,
    Conversa,
    MatriculaDisciplina,
    Mensalidade,
    RoleUsuario,
    Usuario,
)
from app.repositories.usuarios import UsuarioRepository


def test_seed_cria_admin_e_aluno_demo_vinculado(sessao: Session) -> None:
    seed.executar(sessao)

    admin = UsuarioRepository(sessao).buscar_por_login(seed.LOGIN_ADMIN)
    aluno = sessao.scalar(select(Aluno).where(Aluno.cpf == seed.CPF_ALUNO_DEMO))

    assert admin is not None
    assert admin.role is RoleUsuario.ADMIN
    assert admin.aluno_id is None
    assert aluno is not None
    assert aluno.usuarios[0].role is RoleUsuario.ALUNO
    assert aluno.usuarios[0].aluno_id == aluno.id


def test_seed_cria_dados_academicos_e_financeiros(sessao: Session) -> None:
    seed.executar(sessao)

    aluno = sessao.scalar(select(Aluno).where(Aluno.cpf == seed.CPF_ALUNO_DEMO))

    assert sessao.scalar(
        select(func.count()).select_from(MatriculaDisciplina).where(
            MatriculaDisciplina.aluno_id == aluno.id
        )
    ) >= 2
    assert sessao.scalar(
        select(func.count()).select_from(Mensalidade).where(Mensalidade.aluno_id == aluno.id)
    ) >= 2


def test_seed_nao_guarda_senha_em_texto_puro(sessao: Session) -> None:
    seed.executar(sessao)

    admin = UsuarioRepository(sessao).buscar_por_login(seed.LOGIN_ADMIN)

    assert admin.senha_hash != seed.SENHA_DEMO


def test_seed_nao_roda_em_producao(sessao: Session, monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(RuntimeError, match="bloqueado"):
        seed.executar(sessao)


def test_seed_e_idempotente(sessao: Session) -> None:
    seed.executar(sessao)
    contagens = _contagens(sessao)

    seed.executar(sessao)

    assert _contagens(sessao) == contagens


def _contagens(sessao: Session) -> dict[str, int]:
    return {
        modelo.__tablename__: sessao.scalar(select(func.count()).select_from(modelo))
        for modelo in (Aluno, Usuario, MatriculaDisciplina, Mensalidade, Conversa)
    }
