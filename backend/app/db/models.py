"""Modelos SQLAlchemy do domínio académico (PRD seção 4).

Decisões de compatibilidade:
- `native_enum=False`: os ENUMs vêm como VARCHAR + CHECK, iguais em SQLite
  (dev/testes) e PostgreSQL (produção).
- `Uuid`: renderiza CHAR(32) no SQLite e UUID nativo no PostgreSQL.
"""

import enum
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import DateTimeUtc


def _agora() -> datetime:
    """Agora em UTC, com timezone (usado como default das colunas de data)."""
    return datetime.now(timezone.utc)


def _enum_portatil(enum_cls: type[enum.Enum], nome: str) -> SAEnum:
    """ENUM portátil: guarda o `.value` e valida via CHECK constraint."""
    return SAEnum(
        enum_cls,
        name=nome,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda membros: [membro.value for membro in membros],
        length=20,
    )


class StatusMatricula(str, enum.Enum):
    ATIVO = "ATIVO"
    TRANCADO = "TRANCADO"
    CONCLUIDO = "CONCLUIDO"
    INADIMPLENTE = "INADIMPLENTE"


class StatusDisciplina(str, enum.Enum):
    EM_ANDAMENTO = "EM_ANDAMENTO"
    APROVADO = "APROVADO"
    REPROVADO = "REPROVADO"
    AGUARDANDO_NOTA = "AGUARDANDO_NOTA"


class StatusPagamento(str, enum.Enum):
    PENDENTE = "PENDENTE"
    PAGO = "PAGO"
    ATRASADO = "ATRASADO"


class RoleUsuario(str, enum.Enum):
    ALUNO = "ALUNO"
    ADMIN = "ADMIN"


class StatusConversa(str, enum.Enum):
    ABERTA = "ABERTA"
    FECHADA = "FECHADA"


class MotivoFechamento(str, enum.Enum):
    LOGOUT = "LOGOUT"
    TIMEOUT = "TIMEOUT"


class Aluno(Base):
    """Dados cadastrais do estudante (PRD 4.1)."""

    __tablename__ = "alunos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    cpf: Mapped[str] = mapped_column(String(11), unique=True, nullable=False)
    nome_completo: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(160), nullable=False)
    telefone: Mapped[str | None] = mapped_column(String(20))
    curso: Mapped[str | None] = mapped_column(String(120))
    polo: Mapped[str | None] = mapped_column(String(120))
    status_matricula: Mapped[StatusMatricula] = mapped_column(
        _enum_portatil(StatusMatricula, "status_matricula"),
        default=StatusMatricula.ATIVO,
        nullable=False,
    )

    matriculas: Mapped[list["MatriculaDisciplina"]] = relationship(
        back_populates="aluno", cascade="all, delete-orphan"
    )
    mensalidades: Mapped[list["Mensalidade"]] = relationship(
        back_populates="aluno", cascade="all, delete-orphan"
    )
    usuarios: Mapped[list["Usuario"]] = relationship(
        back_populates="aluno", cascade="all, delete-orphan"
    )
    conversas: Mapped[list["Conversa"]] = relationship(
        back_populates="aluno", cascade="all, delete-orphan"
    )
    solicitacoes: Mapped[list["SolicitacaoDocumento"]] = relationship(
        back_populates="aluno", cascade="all, delete-orphan"
    )


class Disciplina(Base):
    """Catálogo de unidades curriculares do curso EAD (PRD 4.2)."""

    __tablename__ = "disciplinas"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    semestre_ideal: Mapped[int] = mapped_column(nullable=False)

    matriculas: Mapped[list["MatriculaDisciplina"]] = relationship(
        back_populates="disciplina", cascade="all, delete-orphan"
    )


class MatriculaDisciplina(Base):
    """Desempenho e notas do aluno por disciplina (PRD 4.3)."""

    __tablename__ = "matriculas_disciplinas"
    __table_args__ = (
        UniqueConstraint(
            "aluno_id", "disciplina_id", "semestre_letivo", name="uq_matricula_aluno_disciplina_semestre"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    aluno_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("alunos.id"), index=True, nullable=False)
    disciplina_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("disciplinas.id"), index=True, nullable=False
    )
    semestre_letivo: Mapped[str] = mapped_column(String(10), nullable=False)
    nota_av1: Mapped[float | None] = mapped_column(Float)
    nota_av2: Mapped[float | None] = mapped_column(Float)
    nota_final: Mapped[float | None] = mapped_column(Float)
    status_disciplina: Mapped[StatusDisciplina] = mapped_column(
        _enum_portatil(StatusDisciplina, "status_disciplina"),
        default=StatusDisciplina.EM_ANDAMENTO,
        nullable=False,
    )

    aluno: Mapped[Aluno] = relationship(back_populates="matriculas")
    disciplina: Mapped[Disciplina] = relationship(back_populates="matriculas")


class Mensalidade(Base):
    """Gestão financeira e boletos do aluno (PRD 4.4)."""

    __tablename__ = "mensalidades"
    __table_args__ = (
        UniqueConstraint("aluno_id", "mes_referencia", name="uq_mensalidade_aluno_mes"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    aluno_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("alunos.id"), index=True, nullable=False)
    mes_referencia: Mapped[str] = mapped_column(String(7), nullable=False)
    valor_original: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    data_vencimento: Mapped[date] = mapped_column(Date, nullable=False)
    status_pagamento: Mapped[StatusPagamento] = mapped_column(
        _enum_portatil(StatusPagamento, "status_pagamento"),
        default=StatusPagamento.PENDENTE,
        nullable=False,
    )
    linha_digitavel: Mapped[str | None] = mapped_column(String(80))
    qr_code_pix: Mapped[str | None] = mapped_column(Text)

    aluno: Mapped[Aluno] = relationship(back_populates="mensalidades")


class SolicitacaoDocumento(Base):
    """Log de auditoria de documentos gerados pelo assistente (PRD 4.5)."""

    __tablename__ = "solicitacoes_documentos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    aluno_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("alunos.id"), index=True, nullable=False)
    tipo_documento: Mapped[str] = mapped_column(String(60), nullable=False)
    enviado_para_email: Mapped[str] = mapped_column(String(160), nullable=False)
    data_emissao: Mapped[datetime] = mapped_column(
        DateTimeUtc, default=_agora, nullable=False
    )

    aluno: Mapped[Aluno] = relationship(back_populates="solicitacoes")


class Usuario(Base):
    """Controle de acesso ao portal (login aluno/admin)."""

    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    login: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleUsuario] = mapped_column(
        _enum_portatil(RoleUsuario, "role_usuario"), nullable=False
    )
    aluno_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("alunos.id"), index=True, nullable=True
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    aluno: Mapped[Aluno | None] = relationship(back_populates="usuarios")


class Conversa(Base):
    """Registro de sessão do aluno no chat, para rastreio E2E."""

    __tablename__ = "conversas"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    aluno_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("alunos.id"), index=True, nullable=False)
    status: Mapped[StatusConversa] = mapped_column(
        _enum_portatil(StatusConversa, "status_conversa"),
        default=StatusConversa.ABERTA,
        nullable=False,
    )
    data_inicio: Mapped[datetime] = mapped_column(
        DateTimeUtc, default=_agora, nullable=False
    )
    data_fim: Mapped[datetime | None] = mapped_column(DateTimeUtc)
    motivo_fechamento: Mapped[MotivoFechamento | None] = mapped_column(
        _enum_portatil(MotivoFechamento, "motivo_fechamento")
    )
    thread_id_foundry: Mapped[str | None] = mapped_column(String(255), unique=True)

    aluno: Mapped[Aluno] = relationship(back_populates="conversas")
