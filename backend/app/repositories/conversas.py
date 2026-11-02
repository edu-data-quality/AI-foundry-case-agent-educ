"""Repositório de conversas (sessão do aluno no chat)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Conversa, MotivoFechamento, StatusConversa


class ConversaRepository:
    """Abre e fecha sessões de chat, mantendo o rastreio por aluno."""

    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def abrir(
        self, aluno_id: uuid.UUID, thread_id_foundry: str | None = None
    ) -> Conversa:
        """Abre uma conversa para o aluno.

        O histórico aceita várias sessões por aluno (inclusive mais de uma
        ABERTA, se uma sessão antiga não teve TIMEOUT registrado). `abrir` não
        recusa: quem consulta usa `buscar_aberta_por_aluno`, que devolve a
        mais recente.
        """
        conversa = Conversa(
            aluno_id=aluno_id,
            status=StatusConversa.ABERTA,
            thread_id_foundry=thread_id_foundry,
        )
        self._sessao.add(conversa)
        self._sessao.commit()
        return conversa

    def fechar(self, conversa_id: uuid.UUID, motivo: MotivoFechamento) -> Conversa:
        """Fecha a conversa registrando motivo e data de fim."""
        conversa = self.buscar_por_id(conversa_id)
        if conversa is None:
            raise ValueError(f"conversa {conversa_id} não encontrada")
        if conversa.status is StatusConversa.FECHADA:
            raise ValueError(f"conversa {conversa_id} já está fechada")
        conversa.status = StatusConversa.FECHADA
        conversa.motivo_fechamento = motivo
        conversa.data_fim = datetime.now(timezone.utc)
        self._sessao.commit()
        return conversa

    def buscar_por_id(self, conversa_id: uuid.UUID) -> Conversa | None:
        """Busca pelo id interno."""
        return self._sessao.get(Conversa, conversa_id)

    def buscar_aberta_por_aluno(self, aluno_id: uuid.UUID) -> Conversa | None:
        """Retorna a conversa ABERTA mais recente do aluno, se existir.

        `first()` com ordenação decrescente (nunca `one_or_none()`): sessões
        antigas sem TIMEOUT podem deixar mais de uma linha ABERTA, e uma
        consulta estrita estouraria `MultipleResultsFound` (HTTP 500).
        """
        return self._sessao.scalars(
            select(Conversa)
            .where(
                Conversa.aluno_id == aluno_id,
                Conversa.status == StatusConversa.ABERTA,
            )
            .order_by(Conversa.data_inicio.desc())
        ).first()
