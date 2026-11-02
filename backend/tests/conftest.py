"""Fixtures compartilhadas pelos testes do backend."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import models  # noqa: F401  (registra as tabelas na metadata)
from app.db.base import Base
from app.db.session import criar_engine

BACKEND = Path(__file__).resolve().parents[1]


def aplicar_migracoes(url: str) -> None:
    """Roda `alembic upgrade head` contra a URL informada."""
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")


@pytest.fixture()
def sessao() -> Iterator[Session]:
    """Sessão SQLite em memória criada por `create_all` (rápida, para unidades)."""
    engine = criar_engine("sqlite://")
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
