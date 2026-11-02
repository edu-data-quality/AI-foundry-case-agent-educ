"""Schema inicial: tabelas transacionais, usuarios e conversas

Revision ID: 0001_schema_inicial
Revises:
Create Date: 2026-11-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_schema_inicial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enum(valores: list[str], nome: str) -> sa.Enum:
    """ENUM portátil (VARCHAR + CHECK), igual em SQLite e PostgreSQL."""
    return sa.Enum(
        *valores,
        name=nome,
        native_enum=False,
        create_constraint=True,
        length=20,
    )


def upgrade() -> None:
    op.create_table(
        "alunos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cpf", sa.String(length=11), nullable=False),
        sa.Column("nome_completo", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=160), nullable=False),
        sa.Column("telefone", sa.String(length=20), nullable=True),
        sa.Column("curso", sa.String(length=120), nullable=True),
        sa.Column("polo", sa.String(length=120), nullable=True),
        sa.Column(
            "status_matricula",
            _enum(["ATIVO", "TRANCADO", "CONCLUIDO", "INADIMPLENTE"], "status_matricula"),
            server_default="ATIVO",
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cpf"),
    )

    op.create_table(
        "disciplinas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("codigo", sa.String(length=20), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("semestre_ideal", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo"),
    )

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("login", sa.String(length=80), nullable=False),
        sa.Column("senha_hash", sa.String(length=255), nullable=False),
        sa.Column("role", _enum(["ALUNO", "ADMIN"], "role_usuario"), nullable=False),
        sa.Column("aluno_id", sa.Uuid(), nullable=True),
        sa.Column("ativo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.ForeignKeyConstraint(["aluno_id"], ["alunos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("login"),
    )
    op.create_index("ix_usuarios_aluno_id", "usuarios", ["aluno_id"])

    op.create_table(
        "matriculas_disciplinas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("aluno_id", sa.Uuid(), nullable=False),
        sa.Column("disciplina_id", sa.Uuid(), nullable=False),
        sa.Column("semestre_letivo", sa.String(length=10), nullable=False),
        sa.Column("nota_av1", sa.Float(), nullable=True),
        sa.Column("nota_av2", sa.Float(), nullable=True),
        sa.Column("nota_final", sa.Float(), nullable=True),
        sa.Column(
            "status_disciplina",
            _enum(
                ["EM_ANDAMENTO", "APROVADO", "REPROVADO", "AGUARDANDO_NOTA"],
                "status_disciplina",
            ),
            server_default="EM_ANDAMENTO",
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["aluno_id"], ["alunos.id"]),
        sa.ForeignKeyConstraint(["disciplina_id"], ["disciplinas.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "aluno_id",
            "disciplina_id",
            "semestre_letivo",
            name="uq_matricula_aluno_disciplina_semestre",
        ),
    )
    op.create_index("ix_matriculas_disciplinas_aluno_id", "matriculas_disciplinas", ["aluno_id"])
    op.create_index(
        "ix_matriculas_disciplinas_disciplina_id", "matriculas_disciplinas", ["disciplina_id"]
    )

    op.create_table(
        "mensalidades",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("aluno_id", sa.Uuid(), nullable=False),
        sa.Column("mes_referencia", sa.String(length=7), nullable=False),
        sa.Column("valor_original", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("data_vencimento", sa.Date(), nullable=False),
        sa.Column(
            "status_pagamento",
            _enum(["PENDENTE", "PAGO", "ATRASADO"], "status_pagamento"),
            server_default="PENDENTE",
            nullable=False,
        ),
        sa.Column("linha_digitavel", sa.String(length=80), nullable=True),
        sa.Column("qr_code_pix", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["aluno_id"], ["alunos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("aluno_id", "mes_referencia", name="uq_mensalidade_aluno_mes"),
    )
    op.create_index("ix_mensalidades_aluno_id", "mensalidades", ["aluno_id"])

    op.create_table(
        "solicitacoes_documentos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("aluno_id", sa.Uuid(), nullable=False),
        sa.Column("tipo_documento", sa.String(length=60), nullable=False),
        sa.Column("enviado_para_email", sa.String(length=160), nullable=False),
        sa.Column(
            "data_emissao", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["aluno_id"], ["alunos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_solicitacoes_documentos_aluno_id", "solicitacoes_documentos", ["aluno_id"])

    op.create_table(
        "conversas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("aluno_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            _enum(["ABERTA", "FECHADA"], "status_conversa"),
            server_default="ABERTA",
            nullable=False,
        ),
        sa.Column(
            "data_inicio", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("data_fim", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "motivo_fechamento",
            _enum(["LOGOUT", "TIMEOUT"], "motivo_fechamento"),
            nullable=True,
        ),
        sa.Column("thread_id_foundry", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["aluno_id"], ["alunos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id_foundry"),
    )
    op.create_index("ix_conversas_aluno_id", "conversas", ["aluno_id"])


def downgrade() -> None:
    op.drop_index("ix_conversas_aluno_id", table_name="conversas")
    op.drop_table("conversas")
    op.drop_index("ix_solicitacoes_documentos_aluno_id", table_name="solicitacoes_documentos")
    op.drop_table("solicitacoes_documentos")
    op.drop_index("ix_mensalidades_aluno_id", table_name="mensalidades")
    op.drop_table("mensalidades")
    op.drop_index(
        "ix_matriculas_disciplinas_disciplina_id", table_name="matriculas_disciplinas"
    )
    op.drop_index("ix_matriculas_disciplinas_aluno_id", table_name="matriculas_disciplinas")
    op.drop_table("matriculas_disciplinas")
    op.drop_index("ix_usuarios_aluno_id", table_name="usuarios")
    op.drop_table("usuarios")
    op.drop_table("disciplinas")
    op.drop_table("alunos")
