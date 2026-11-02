"""Repositório de solicitações de documentos (log de auditoria)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import SolicitacaoDocumento


class SolicitacaoDocumentoRepository:
    """Registra documentos emitidos pelo assistente."""

    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def registrar(
        self, *, aluno_id: uuid.UUID, tipo_documento: str, enviado_para_email: str
    ) -> SolicitacaoDocumento:
        """Registra a emissão de um documento."""
        solicitacao = SolicitacaoDocumento(
            aluno_id=aluno_id,
            tipo_documento=tipo_documento,
            enviado_para_email=enviado_para_email,
        )
        self._sessao.add(solicitacao)
        self._sessao.commit()
        return solicitacao

    def listar_por_aluno(self, aluno_id: uuid.UUID) -> list[SolicitacaoDocumento]:
        """Lista as solicitações do aluno, da mais recente para a mais antiga."""
        return list(
            self._sessao.scalars(
                select(SolicitacaoDocumento)
                .where(SolicitacaoDocumento.aluno_id == aluno_id)
                .order_by(SolicitacaoDocumento.data_emissao.desc())
            )
        )
