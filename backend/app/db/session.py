"""Criação de engine e sessão do banco.

`DATABASE_URL` define o alvo: SQLite por padrão no dev local e PostgreSQL no
`docker-compose` (ver ADR-0001).
"""

import os
import sqlite3
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL_PADRAO = "sqlite:///./ead.db"


def get_database_url() -> str:
    """URL do banco em uso, com fallback para SQLite local."""
    return os.getenv("DATABASE_URL", DATABASE_URL_PADRAO)


def criar_engine(url: str | None = None) -> Engine:
    """Cria a engine, ajustando o SQLite (threads e integridade referencial)."""
    url = url or get_database_url()
    opcoes: dict[str, Any] = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        opcoes["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **opcoes)
    if url.startswith("sqlite"):
        event.listen(engine, "connect", _habilitar_chaves_estrangeiras)
    return engine


def _habilitar_chaves_estrangeiras(
    conexao: sqlite3.Connection, _registro: Any
) -> None:
    """SQLite ignora FKs por padrão; o PostgreSQL as aplica. Igualar o comportamento."""
    cursor = conexao.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


engine = criar_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Session:
    """Sessão nova para uso em repositórios e scripts."""
    return SessionLocal()
