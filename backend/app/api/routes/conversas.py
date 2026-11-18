"""Sessões/threads do chat (issue #11): abrir, fechar e listar.

Regras de escopo:
- `ALUNO` abre e fecha apenas a própria sessão; a identidade vem do token
  (`usuario.aluno_id`), nunca do corpo da requisição.
- `ADMIN` pode listar todas as sessões e fechar qualquer uma (observabilidade).
- No máximo uma conversa ABERTA por aluno: `POST /api/conversas` retoma a
  existente em vez de criar outra.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import (
    exigir_aluno,
    garantir_acesso_aluno,
    get_usuario_atual,
)
from app.db.models import (
    Conversa,
    MotivoFechamento,
    RoleUsuario,
    StatusConversa,
    Usuario,
)
from app.db.session import get_db
from app.repositories.conversas import (
    LIMITE_LISTAGEM_MAXIMO,
    LIMITE_LISTAGEM_PADRAO,
    ConversaRepository,
)

router = APIRouter(prefix="/api/conversas", tags=["conversas"])


class AbrirConversaRequest(BaseModel):
    """Corpo opcional do `POST /api/conversas`.

    `thread_id_foundry` é preenchido pela integração com o Foundry (S12);
    quando omitido, a sessão nasce sem thread.
    """

    thread_id_foundry: str | None = None


class ConversaResposta(BaseModel):
    """Contrato de uma sessão de chat (rastreio E2E)."""

    id: str
    aluno_id: str
    status: StatusConversa
    data_inicio: datetime
    ultima_interacao: datetime
    data_fim: datetime | None = None
    motivo_fechamento: MotivoFechamento | None = None
    thread_id_foundry: str | None = None


def _serializar(conversa: Conversa) -> ConversaResposta:
    return ConversaResposta(
        id=str(conversa.id),
        aluno_id=str(conversa.aluno_id),
        status=conversa.status,
        data_inicio=conversa.data_inicio,
        ultima_interacao=conversa.ultima_interacao,
        data_fim=conversa.data_fim,
        motivo_fechamento=conversa.motivo_fechamento,
        thread_id_foundry=conversa.thread_id_foundry,
    )


@router.post(
    "",
    response_model=ConversaResposta,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Token ausente ou inválido"},
        403: {"description": "Usuário autenticado não é aluno"},
    },
)
def abrir_conversa(
    payload: AbrirConversaRequest | None = None,
    usuario: Usuario = Depends(get_usuario_atual),
    sessao: Session = Depends(get_db),
) -> ConversaResposta:
    """Abre a sessão do aluno logado ou retoma a que já está ABERTA."""
    aluno_id = exigir_aluno(usuario)
    conversa = ConversaRepository(sessao).abrir_ou_continuar(
        aluno_id, payload.thread_id_foundry if payload else None
    )
    return _serializar(conversa)


@router.post(
    "/{conversa_id}/fechar",
    response_model=ConversaResposta,
    responses={
        401: {"description": "Token ausente ou inválido"},
        403: {"description": "Sessão de outro aluno"},
        404: {"description": "Sessão inexistente"},
        409: {"description": "Sessão já fechada"},
    },
)
def fechar_conversa(
    conversa_id: uuid.UUID,
    usuario: Usuario = Depends(get_usuario_atual),
    sessao: Session = Depends(get_db),
) -> ConversaResposta:
    """Fecha a sessão no logout, registrando motivo LOGOUT e data de fim."""
    repo = ConversaRepository(sessao)
    conversa = repo.buscar_por_id(conversa_id)
    if conversa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="conversa não encontrada",
        )
    garantir_acesso_aluno(usuario, conversa.aluno_id)
    try:
        fechada = repo.fechar(conversa_id, MotivoFechamento.LOGOUT)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return _serializar(fechada)


@router.get(
    "",
    response_model=list[ConversaResposta],
    responses={
        401: {"description": "Token ausente ou inválido"},
        403: {"description": "Aluno consultando sessões de outro aluno"},
    },
)
def listar_conversas(
    aluno_id: uuid.UUID | None = Query(
        None, description="Filtro por aluno (apenas ADMIN)"
    ),
    limite: int = Query(LIMITE_LISTAGEM_PADRAO, ge=1, le=LIMITE_LISTAGEM_MAXIMO),
    offset: int = Query(0, ge=0),
    usuario: Usuario = Depends(get_usuario_atual),
    sessao: Session = Depends(get_db),
) -> list[ConversaResposta]:
    """Lista sessões para observabilidade/analytics.

    Aluno vê apenas as próprias; ADMIN vê todas e pode filtrar por `aluno_id`.
    """
    if usuario.role is RoleUsuario.ADMIN:
        filtro = aluno_id
    else:
        # `exigir_aluno` recusa ALUNO sem vínculo; sem isso o filtro viraria
        # `None` e a listagem devolveria as sessões de todos os alunos.
        proprio = exigir_aluno(usuario)
        if aluno_id is not None and aluno_id != proprio:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="acesso restrito às próprias sessões",
            )
        filtro = proprio

    conversas = ConversaRepository(sessao).listar(
        aluno_id=filtro, limite=limite, offset=offset
    )
    return [_serializar(conversa) for conversa in conversas]


@router.get(
    "/{conversa_id}",
    response_model=ConversaResposta,
    responses={
        401: {"description": "Token ausente ou inválido"},
        403: {"description": "Sessão de outro aluno"},
        404: {"description": "Sessão inexistente"},
    },
)
def detalhar_conversa(
    conversa_id: uuid.UUID,
    usuario: Usuario = Depends(get_usuario_atual),
    sessao: Session = Depends(get_db),
) -> ConversaResposta:
    """Detalha uma sessão (auditoria de início/fim/motivo)."""
    conversa = ConversaRepository(sessao).buscar_por_id(conversa_id)
    if conversa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="conversa não encontrada",
        )
    garantir_acesso_aluno(usuario, conversa.aluno_id)
    return _serializar(conversa)
