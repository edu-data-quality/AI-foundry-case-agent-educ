"""Testes das migrações Alembic."""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.db import models  # noqa: F401  (registra as tabelas na metadata)
from app.db.base import Base

BACKEND = Path(__file__).resolve().parents[1]

TABELAS_ESPERADAS = {
    "alunos",
    "disciplinas",
    "matriculas_disciplinas",
    "mensalidades",
    "solicitacoes_documentos",
    "usuarios",
    "conversas",
}


def _aplicar_migracoes(url: str) -> None:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")


def test_migracao_cria_todas_as_tabelas(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'migrado.db'}"

    _aplicar_migracoes(url)

    inspetor = inspect(create_engine(url))
    assert TABELAS_ESPERADAS <= set(inspetor.get_table_names())


def test_schema_migrado_igual_ao_dos_modelos(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'migrado.db'}"
    _aplicar_migracoes(url)
    inspetor = inspect(create_engine(url))

    for tabela in TABELAS_ESPERADAS:
        colunas_migracao = {coluna["name"] for coluna in inspetor.get_columns(tabela)}
        colunas_modelo = set(Base.metadata.tables[tabela].columns.keys())
        assert colunas_migracao == colunas_modelo, f"divergência em {tabela}"


def test_migracao_nao_gera_drift_contra_os_modelos(tmp_path: Path) -> None:
    """`alembic revision --autogenerate` deve sair vazio: migração == modelos."""
    url = f"sqlite:///{tmp_path / 'migrado.db'}"
    _aplicar_migracoes(url)
    engine = create_engine(url)

    with engine.connect() as conexao:
        contexto = MigrationContext.configure(conexao)
        diferencas = compare_metadata(contexto, Base.metadata)

    assert diferencas == []


def test_migracao_e_idempotente(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'migrado.db'}"

    _aplicar_migracoes(url)
    _aplicar_migracoes(url)

    inspetor = inspect(create_engine(url))
    assert TABELAS_ESPERADAS <= set(inspetor.get_table_names())
