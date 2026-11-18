"""Adiciona `ultima_interacao` em conversas (job de timeout da sessão)

Revision ID: 0002_conversa_ultima_interacao
Revises: 0001_schema_inicial
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_conversa_ultima_interacao"
down_revision: str | None = "0001_schema_inicial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _fechar_abertas_duplicadas(conexao) -> None:
    """Fecha ABERTAS duplicadas antes do índice único parcial.

    O schema anterior admitia mais de uma ABERTA por aluno. Em banco legado,
    `create_index` falharia. Mantém a sessão mais recente e fecha as demais
    como TIMEOUT (o motivo real é desconhecido; TIMEOUT é o fallback).
    """
    linhas = conexao.execute(
        sa.text(
            "SELECT aluno_id, id FROM conversas "
            "WHERE status = 'ABERTA' "
            "ORDER BY aluno_id, data_inicio DESC, id"
        )
    ).fetchall()
    vistos: set = set()
    duplicadas = []
    for aluno_id, conversa_id in linhas:
        if aluno_id in vistos:
            duplicadas.append(conversa_id)
        else:
            vistos.add(aluno_id)

    for conversa_id in duplicadas:
        conexao.execute(
            sa.text(
                "UPDATE conversas SET status = 'FECHADA', "
                "motivo_fechamento = 'TIMEOUT', data_fim = CURRENT_TIMESTAMP "
                "WHERE id = :id"
            ),
            {"id": conversa_id},
        )


def upgrade() -> None:
    # SQLite recusa `ADD COLUMN NOT NULL DEFAULT CURRENT_TIMESTAMP` em tabela
    # com linhas. Adiciona nullable, backfill a partir de `data_inicio`, e só
    # então aplica NOT NULL + default via batch (recria a tabela no SQLite).
    with op.batch_alter_table("conversas") as batch:
        batch.add_column(
            sa.Column("ultima_interacao", sa.DateTime(timezone=True), nullable=True)
        )
    op.execute(
        "UPDATE conversas SET ultima_interacao = data_inicio "
        "WHERE ultima_interacao IS NULL"
    )
    with op.batch_alter_table("conversas") as batch:
        batch.alter_column(
            "ultima_interacao",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        )

    _fechar_abertas_duplicadas(op.get_bind())
    # Regra "uma ABERTA por aluno" no banco. Índice parcial: só as linhas
    # ABERTAS disputam a unicidade por aluno.
    op.create_index(
        "uq_conversas_aluno_aberta",
        "conversas",
        ["aluno_id"],
        unique=True,
        sqlite_where=sa.text("status = 'ABERTA'"),
        postgresql_where=sa.text("status = 'ABERTA'"),
    )


def downgrade() -> None:
    op.drop_index("uq_conversas_aluno_aberta", table_name="conversas")
    op.drop_column("conversas", "ultima_interacao")
