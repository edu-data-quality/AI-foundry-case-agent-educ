"""Emissão de declaração de matrícula (issue #6 / US1.2 do PRD).

Contrato do PRD: `POST /api/declaracoes/gerar` com
`{"aluno_id": "uuid", "tipo": "matricula"}`. O aluno_id vem no corpo porque a
tool do Foundry declara em nome de um aluno; a autorização continua vindo do
token:

- `ALUNO` só emite para si mesmo; aluno_id de outro (inclusive inexistente)
  recebe 403, para não permitir enumeração de ids.
- `ADMIN` emite para qualquer aluno; id inexistente recebe 404.

Fluxo: resolve o aluno, valida o e-mail cadastrado, gera o PDF do template
HTML, envia pelo Resend e registra a solicitação em `solicitacoes_documentos`.
Sem `RESEND_API_KEY` o envio é simulado (`status: "simulado"`), nunca fingido
como sucesso.
"""

import uuid
from enum import Enum
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.api.deps import get_usuario_atual
from app.db.models import Aluno, RoleUsuario, Usuario
from app.db.session import get_db
from app.declaracoes import (
    DadosDeclaracao,
    ErroEnvioEmail,
    enviar_email_declaracao,
    gerar_pdf_matricula,
)
from app.repositories.alunos import AlunoRepository
from app.repositories.documentos import SolicitacaoDocumentoRepository

router = APIRouter(prefix="/api/declaracoes", tags=["declaracoes"])

_validador_email = TypeAdapter(EmailStr)


class TipoDocumento(str, Enum):
    """Tipos de documento suportados pelo endpoint."""

    MATRICULA = "matricula"


class RequisicaoDeclaracao(BaseModel):
    """Payload do `POST /api/declaracoes/gerar` (PRD seção 5)."""

    aluno_id: uuid.UUID
    tipo: TipoDocumento = TipoDocumento.MATRICULA


class RespostaDeclaracao(BaseModel):
    """Contrato de retorno do PRD; `simulado` sinaliza o modo dev sem chave."""

    status: Literal["sucesso", "simulado"]
    email_destino: EmailStr


def _resolver_aluno(
    usuario: Usuario, aluno_id: uuid.UUID, sessao: Session
) -> Aluno:
    """Resolve o aluno do pedido respeitando o escopo da role."""
    if usuario.role is RoleUsuario.ALUNO:
        if usuario.aluno is None or usuario.aluno_id != aluno_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="acesso restrito aos próprios dados",
            )
        return usuario.aluno

    aluno = AlunoRepository(sessao).buscar_por_id(aluno_id)
    if aluno is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="aluno não encontrado",
        )
    return aluno


def _validar_email(email: str) -> str:
    """Valida o e-mail cadastrado antes de gerar PDF e chamar o provedor."""
    try:
        return str(_validador_email.validate_python(email))
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail="e-mail do aluno inválido",
        ) from exc


@router.post(
    "/gerar",
    response_model=RespostaDeclaracao,
    status_code=status.HTTP_200_OK,
    responses={
        403: {"description": "Aluno autenticado emitindo para outro aluno"},
        404: {"description": "aluno_id não cadastrado (emissão por ADMIN)"},
        422: {"description": "tipo desconhecido, UUID inválido ou e-mail do aluno inválido"},
        502: {"description": "Falha no envio do e-mail pelo provedor"},
    },
)
def gerar_declaracao(
    requisicao: RequisicaoDeclaracao,
    usuario: Usuario = Depends(get_usuario_atual),
    sessao: Session = Depends(get_db),
) -> RespostaDeclaracao:
    """Gera a declaração em PDF, envia por e-mail e registra a auditoria.

    Erros: 401 sem token válido; 403 para aluno emitindo para outro aluno_id,
    inclusive inexistente; 404 para aluno_id desconhecido emitido por ADMIN;
    422 para payload/e-mail inválido; 502 quando o Resend falha.
    """
    aluno = _resolver_aluno(usuario, requisicao.aluno_id, sessao)
    email_destino = _validar_email(aluno.email)

    dados = DadosDeclaracao(
        nome_completo=aluno.nome_completo,
        cpf=aluno.cpf,
        email=email_destino,
        curso=aluno.curso,
        polo=aluno.polo,
    )
    pdf = gerar_pdf_matricula(dados)

    try:
        enviado = enviar_email_declaracao(dados, pdf)
    except ErroEnvioEmail as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"falha ao enviar e-mail: {exc}",
        ) from exc

    SolicitacaoDocumentoRepository(sessao).registrar(
        aluno_id=aluno.id,
        tipo_documento=requisicao.tipo.value,
        enviado_para_email=email_destino,
    )

    return RespostaDeclaracao(
        status="sucesso" if enviado else "simulado",
        email_destino=email_destino,
    )
