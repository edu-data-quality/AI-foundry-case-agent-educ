"""Endpoints administrativos (issue #7 / PRD 5, US1.3 e US4.2).

Permitem ao ADMIN (painel e tools do Foundry) injetar e alterar dados em tempo
real — cadastro de aluno e mudança de notas, boletos e matrícula — para
validar o ciclo E2E do agente (S4/S5).

Todas as rotas exigem `role == ADMIN` via `requer_admin`; aluno autenticado
recebe 403 (nunca 404).

Regra de consistência:
- A matrícula lançada deve pertencer ao aluno do path; caso contrário, 404
  (recurso inexistente), evitando acoplar dados de outro aluno.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.deps import requer_admin
from app.db.models import (
    StatusDisciplina,
    StatusMatricula,
    StatusPagamento,
)
from app.db.session import get_db
from app.repositories.academico import MatriculaRepository
from app.repositories.alunos import AlunoRepository
from app.repositories.financeiro import MensalidadeRepository

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CadastroAluno(BaseModel):
    """Dados cadastrais de um novo aluno para testes E2E (US1.3)."""

    cpf: str = Field(pattern=r"^\d{11}$", description="CPF do aluno, 11 dígitos")
    nome_completo: str = Field(min_length=3, description="Nome completo do aluno")
    email: EmailStr
    telefone: str | None = None
    curso: str | None = None
    polo: str | None = None
    status_matricula: StatusMatricula = StatusMatricula.ATIVO


class AlunoResposta(BaseModel):
    """Contrato de retorno do cadastro/consulta de aluno."""

    id: str
    cpf: str
    nome_completo: str
    email: EmailStr
    telefone: str | None = None
    curso: str | None = None
    polo: str | None = None
    status_matricula: StatusMatricula


class DisciplinaAlunoResposta(BaseModel):
    """Notas e situação do aluno em uma disciplina (detalhe admin).

    `matricula_id` é o identificador usado pelo simulador (US4.2) para lançar
    notas via `PATCH /api/admin/alunos/{aluno_id}/matriculas/{matricula_id}/notas`.
    """

    matricula_id: str
    disciplina_id: str
    codigo: str
    nome: str
    semestre_letivo: str
    nota_av1: float | None = None
    nota_av2: float | None = None
    nota_final: float | None = None
    status_disciplina: StatusDisciplina


class MensalidadeAlunoResposta(BaseModel):
    """Boleto/mensalidade exibido no detalhe do aluno (detalhe admin)."""

    id: str
    aluno_id: str
    mes_referencia: str
    valor_original: float
    data_vencimento: date
    status_pagamento: StatusPagamento


class AlunoDetalheResposta(BaseModel):
    """Contrato do `GET /api/admin/alunos/{aluno_id}`: aluno + histórico."""

    aluno: AlunoResposta
    disciplinas: list[DisciplinaAlunoResposta]
    mensalidades: list[MensalidadeAlunoResposta]


class NotasMatricula(BaseModel):
    """Notas e situação lançadas pelo ADMIN em uma matrícula (US4.2)."""

    nota_av1: float | None = None
    nota_av2: float | None = None
    nota_final: float | None = None
    status_disciplina: StatusDisciplina


class MatriculaResposta(BaseModel):
    """Contrato de retorno das notas lançadas."""

    id: str
    disciplina_id: str
    semestre_letivo: str
    nota_av1: float | None = None
    nota_av2: float | None = None
    nota_final: float | None = None
    status_disciplina: StatusDisciplina


class StatusPagamentoPayload(BaseModel):
    """Novo status de boleto (PENDENTE/PAGO/ATRASADO)."""

    status: StatusPagamento


class MensalidadeResposta(BaseModel):
    """Contrato de retorno da alteração de status do boleto."""

    id: str
    aluno_id: str
    mes_referencia: str
    status_pagamento: StatusPagamento


class StatusMatriculaPayload(BaseModel):
    """Novo status de matrícula do aluno."""

    status: StatusMatricula


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------


def _aluno_ou_404(aluno_id: uuid.UUID, sessao: Session):
    """Resolve o aluno; 404 se não existir."""
    aluno = AlunoRepository(sessao).buscar_por_id(aluno_id)
    if aluno is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="aluno não encontrado",
        )
    return aluno


def _aluno_resposta(aluno) -> AlunoResposta:
    """Converte o modelo ORM no contrato público `AlunoResposta`."""
    return AlunoResposta(
        id=str(aluno.id),
        cpf=aluno.cpf,
        nome_completo=aluno.nome_completo,
        email=aluno.email,
        telefone=aluno.telefone,
        curso=aluno.curso,
        polo=aluno.polo,
        status_matricula=aluno.status_matricula,
    )


@router.get(
    "/alunos",
    response_model=list[AlunoResposta],
    responses={
        403: {"description": "Aluno autenticado tentando usar endpoint admin"},
    },
)
def listar_alunos(
    busca: str | None = Query(
        default=None,
        description="Nome (trecho, case-insensitive) ou CPF (prefixo, só dígitos)",
    ),
    _: object = Depends(requer_admin),
    sessao: Session = Depends(get_db),
) -> list[AlunoResposta]:
    """Lista e busca alunos por nome ou CPF (US4.1 — listagem do painel)."""
    alunos = AlunoRepository(sessao).listar(busca=busca)
    return [_aluno_resposta(aluno) for aluno in alunos]


@router.get(
    "/alunos/{aluno_id}",
    response_model=AlunoDetalheResposta,
    responses={
        403: {"description": "Aluno autenticado tentando usar endpoint admin"},
        404: {"description": "Aluno não encontrado"},
    },
)
def detalhar_aluno(
    aluno_id: uuid.UUID,
    _: object = Depends(requer_admin),
    sessao: Session = Depends(get_db),
) -> AlunoDetalheResposta:
    """Detalhe do aluno com disciplinas e mensalidades (US4.1)."""
    aluno = _aluno_ou_404(aluno_id, sessao)
    matriculas = MatriculaRepository(sessao).listar_por_aluno(aluno.id)
    mensalidades = MensalidadeRepository(sessao).listar_por_aluno(aluno.id)
    return AlunoDetalheResposta(
        aluno=_aluno_resposta(aluno),
        disciplinas=[
            DisciplinaAlunoResposta(
                matricula_id=str(matricula.id),
                disciplina_id=str(matricula.disciplina_id),
                codigo=matricula.disciplina.codigo,
                nome=matricula.disciplina.nome,
                semestre_letivo=matricula.semestre_letivo,
                nota_av1=matricula.nota_av1,
                nota_av2=matricula.nota_av2,
                nota_final=matricula.nota_final,
                status_disciplina=matricula.status_disciplina,
            )
            for matricula in matriculas
        ],
        mensalidades=[
            MensalidadeAlunoResposta(
                id=str(mensalidade.id),
                aluno_id=str(mensalidade.aluno_id),
                mes_referencia=mensalidade.mes_referencia,
                valor_original=float(mensalidade.valor_original),
                data_vencimento=mensalidade.data_vencimento,
                status_pagamento=mensalidade.status_pagamento,
            )
            for mensalidade in mensalidades
        ],
    )


@router.post(
    "/alunos",
    response_model=AlunoResposta,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"description": "Aluno autenticado tentando usar endpoint admin"},
        409: {"description": "CPF já cadastrado"},
        422: {"description": "Dados cadastrais inválidos"},
    },
)
def criar_aluno(
    payload: CadastroAluno,
    _: object = Depends(requer_admin),
    sessao: Session = Depends(get_db),
) -> AlunoResposta:
    """Cadastra um novo aluno com dados fictícios para testes E2E (US1.3)."""
    repo = AlunoRepository(sessao)
    if repo.buscar_por_cpf(payload.cpf) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CPF já cadastrado",
        )
    aluno = repo.criar(
        cpf=payload.cpf,
        nome_completo=payload.nome_completo,
        email=payload.email,
        telefone=payload.telefone,
        curso=payload.curso,
        polo=payload.polo,
        status_matricula=payload.status_matricula,
    )
    return _aluno_resposta(aluno)


@router.patch(
    "/alunos/{aluno_id}/matriculas/{matricula_id}/notas",
    response_model=MatriculaResposta,
    responses={
        403: {"description": "Aluno autenticado tentando usar endpoint admin"},
        404: {"description": "Aluno ou matrícula não encontrados / matrícula de outro aluno"},
        422: {"description": "Payload inválido (nota fora da faixa ou status desconhecido)"},
    },
)
def lancar_notas(
    aluno_id: uuid.UUID,
    matricula_id: uuid.UUID,
    payload: NotasMatricula,
    _: object = Depends(requer_admin),
    sessao: Session = Depends(get_db),
) -> MatriculaResposta:
    """Lança notas AV1/AV2/final e a situação da disciplina (US4.2)."""
    aluno = _aluno_ou_404(aluno_id, sessao)
    matricula = MatriculaRepository(sessao).buscar_por_id(matricula_id)
    if matricula is None or matricula.aluno_id != aluno.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="matrícula não encontrada",
        )
    matricula = MatriculaRepository(sessao).registrar_notas(
        matricula_id,
        nota_av1=payload.nota_av1,
        nota_av2=payload.nota_av2,
        nota_final=payload.nota_final,
        status_disciplina=payload.status_disciplina,
    )
    return MatriculaResposta(
        id=str(matricula.id),
        disciplina_id=str(matricula.disciplina_id),
        semestre_letivo=matricula.semestre_letivo,
        nota_av1=matricula.nota_av1,
        nota_av2=matricula.nota_av2,
        nota_final=matricula.nota_final,
        status_disciplina=matricula.status_disciplina,
    )


@router.patch(
    "/mensalidades/{mensalidade_id}/status",
    response_model=MensalidadeResposta,
    responses={
        403: {"description": "Aluno autenticado tentando usar endpoint admin"},
        404: {"description": "Mensalidade não encontrada"},
        422: {"description": "Status de pagamento desconhecido"},
    },
)
def alterar_status_mensalidade(
    mensalidade_id: uuid.UUID,
    payload: StatusPagamentoPayload,
    _: object = Depends(requer_admin),
    sessao: Session = Depends(get_db),
) -> MensalidadeResposta:
    """Altera o status do boleto (PENDENTE/PAGO/ATRASADO) em runtime (US4.2)."""
    repo = MensalidadeRepository(sessao)
    if repo.buscar_por_id(mensalidade_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="mensalidade não encontrada",
        )
    mensalidade = repo.atualizar_status(mensalidade_id, status_pagamento=payload.status)
    return MensalidadeResposta(
        id=str(mensalidade.id),
        aluno_id=str(mensalidade.aluno_id),
        mes_referencia=mensalidade.mes_referencia,
        status_pagamento=mensalidade.status_pagamento,
    )


@router.patch(
    "/alunos/{aluno_id}/matricula-status",
    response_model=AlunoResposta,
    responses={
        403: {"description": "Aluno autenticado tentando usar endpoint admin"},
        404: {"description": "Aluno não encontrado"},
        422: {"description": "Status de matrícula desconhecido"},
    },
)
def alterar_status_matricula(
    aluno_id: uuid.UUID,
    payload: StatusMatriculaPayload,
    _: object = Depends(requer_admin),
    sessao: Session = Depends(get_db),
) -> AlunoResposta:
    """Altera o status de matrícula (ATIVO/TRANCADO/CONCLUIDO/INADIMPLENTE)."""
    _aluno_ou_404(aluno_id, sessao)
    aluno = AlunoRepository(sessao).atualizar_status_matricula(
        aluno_id, status_matricula=payload.status
    )
    return _aluno_resposta(aluno)