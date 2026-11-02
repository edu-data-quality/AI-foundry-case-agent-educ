"""Fixtures compartilhadas pelos testes do backend."""

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.db import models  # noqa: F401  (registra as tabelas na metadata)
from app.db.base import Base
from app.db.session import criar_engine


@pytest.fixture()
def sessao() -> Iterator[Session]:
    """Sessão SQLite em memória com o schema criado, isolada por teste."""
    engine = criar_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()
