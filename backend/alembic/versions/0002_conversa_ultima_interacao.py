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


def upgrade() -> None:
    # `server_default=now()` preenche as linhas existentes e mantém INSERT via
    # SQL puro funcionando (mesma decisão da migração 0001).
    op.add_column(
        "conversas",
        sa.Column(
            "ultima_interacao",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
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
