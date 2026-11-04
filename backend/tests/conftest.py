"""Fixtures compartilhadas pelos testes do backend."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401  (registra as tabelas na metadata)
from app.db.base import Base
from app.db.session import criar_engine

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def segredo_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ambiente mínimo de autenticação para todos os testes.

    Os módulos leem o segredo e o TTL no momento da chamada, então setar aqui
    basta para emissão e validação de tokens tanto nesses testes quanto nos de
    `test_auth_api.py`.
    """
    monkeypatch.setenv("JWT_SECRET", "segredo-de-teste-pytest-0123456789abcdef")
    monkeypatch.setenv("JWT_EXPIRA_MINUTOS", "60")


def aplicar_migracoes(url: str) -> None:
    """Roda `alembic upgrade head` contra a URL informada."""
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")


@pytest.fixture()
def sessao() -> Iterator[Session]:
    """Sessão SQLite em memória criada por `create_all` (rápida, para unidades).

    `StaticPool` mantém UMA conexão para toda a engine: sem isso, cada request
    do TestClient abriria um banco em memória separado e vazio.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def sessao_migrada(tmp_path: Path) -> Iterator[Session]:
    """Sessão sobre schema criado pela migração real (não pelo ORM).

    Expõe bugs de default do servidor, constraints e FKs que `create_all`
    esconde, porque aqui as colunas vêm do DDL do Alembic.
    """
    url = f"sqlite:///{tmp_path / 'migrado.db'}"
    aplicar_migracoes(url)
    engine = create_engine(url)
    with Session(engine) as session:
        yield session
    engine.dispose()
