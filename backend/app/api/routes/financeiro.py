"""Boletos financeiros do aluno (issue #5 / US1.2 do PRD).

Regra de escopo:
- `ALUNO` consulta apenas o próprio CPF; outro CPF recebe 403.
- `ADMIN` consulta qualquer CPF (painel administrativo e tools do Foundry).
- `ALUNO` nunca recebe 404: CPF diferente do próprio responde 403, inclusive
  quando não existe, para não permitir enumeração de CPFs cadastrados.

Retorna apenas boletos em aberto (PENDENTE/ATRASADO), conforme o contrato da
US1.2 (`linha_digitavel`, `qr_code_pix`, `data_vencimento`, `status_pagamento`).
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_usuario_atual
from app.db.models import Aluno, RoleUsuario, StatusPagamento, Usuario
from app.db.session import get_db
from app.repositories.alunos import AlunoRepository
from app.repositories.financeiro import MensalidadeRepository

router = APIRouter(prefix="/api/financeiro", tags=["financeiro"])


class BoletoResposta(BaseModel):
    """Contrato de um boleto em aberto (`GET /api/financeiro/boleto`)."""

    linha_digitavel: str | None = None
    qr_code_pix: str | None = None
    data_vencimento: date
    status_pagamento: StatusPagamento


def _resolver_aluno(usuario: Usuario, cpf: str, sessao: Session) -> Aluno:
    """Resolve o aluno do request respeitando o escopo da role.

    Para `ALUNO`, a identidade vem do token (`usuario.aluno`), nunca do CPF
    consultado; CPF diferente do próprio é tratado como acesso negado.
    """
    if usuario.role is RoleUsuario.ALUNO:
        aluno = usuario.aluno
        if aluno is None or aluno.cpf != cpf:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="acesso restrito aos próprios dados",
            )
        return aluno

    aluno = AlunoRepository(sessao).buscar_por_cpf(cpf)
    if aluno is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="aluno não encontrado",
        )
    return aluno


@router.get(
    "/boleto",
    response_model=list[BoletoResposta],
    responses={
        403: {"description": "Aluno autenticado consultando CPF de outro aluno"},
        404: {"description": "CPF não cadastrado (consulta de ADMIN)"},
        422: {"description": "CPF fora do formato de 11 dígitos"},
    },
)
def boletos(
    cpf: str = Query(
        ...,
        pattern=r"^\d{11}$",
        description="CPF do aluno, apenas dígitos (11 caracteres)",
    ),
    usuario: Usuario = Depends(get_usuario_atual),
    sessao: Session = Depends(get_db),
) -> list[BoletoResposta]:
    """Retorna os boletos em aberto do aluno.

    Erros: 401 sem token válido; 403 para aluno consultando outro CPF,
    inclusive inexistente, para evitar enumeração; 404 para CPF inexistente
    consultado por ADMIN; 422 para CPF fora do formato de 11 dígitos.
    """
    aluno = _resolver_aluno(usuario, cpf, sessao)
    mensalidades = MensalidadeRepository(sessao).listar_em_aberto_por_aluno(aluno.id)

    return [
        BoletoResposta(
            linha_digitavel=mensalidade.linha_digitavel,
            qr_code_pix=mensalidade.qr_code_pix,
            data_vencimento=mensalidade.data_vencimento,
            status_pagamento=mensalidade.status_pagamento,
        )
        for mensalidade in mensalidades
    ]