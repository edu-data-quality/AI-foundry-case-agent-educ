"""Repositório de conversas (sessão do aluno no chat)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Conversa, MotivoFechamento, StatusConversa

LIMITE_LISTAGEM_PADRAO = 50
LIMITE_LISTAGEM_MAXIMO = 200


class ConversaRepository:
    """Abre e fecha sessões de chat, mantendo o rastreio por aluno."""

    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def abrir(
        self, aluno_id: uuid.UUID, thread_id_foundry: str | None = None
    ) -> Conversa:
        """Abre uma conversa para o aluno.

        O banco garante no máximo uma ABERTA por aluno (índice único parcial).
        Prefira `abrir_ou_continuar` em fluxos de login/chat: chamar `abrir`
        com uma sessão já ABERTA levanta `IntegrityError`.
        """
        conversa = Conversa(
            aluno_id=aluno_id,
            status=StatusConversa.ABERTA,
            thread_id_foundry=thread_id_foundry,
        )
        self._sessao.add(conversa)
        self._sessao.commit()
        return conversa

    def abrir_ou_continuar(
        self, aluno_id: uuid.UUID, thread_id_foundry: str | None = None
    ) -> Conversa:
        """Retorna a sessão ABERTA do aluno ou abre uma nova.

        Regra de negócio: no máximo uma conversa ABERTA por aluno. Se já
        existe, a sessão é retomada, a última interação é atualizada (o
        timeout recomeça) e o `thread_id_foundry` é preenchido quando ainda
        estava vazio.

        Login concorrente: dois logins podem passar juntos pelo `buscar` e o
        segundo INSERT bate no índice único. Nesse caso o `IntegrityError` é
        tratado como "outro login abriu a sessão": recarrega e retoma.
        """
        conversa = self.buscar_aberta_por_aluno(aluno_id)
        if conversa is None:
            try:
                return self.abrir(aluno_id, thread_id_foundry)
            except IntegrityError:
                self._sessao.rollback()
                conversa = self.buscar_aberta_por_aluno(aluno_id)
                if conversa is None:
                    raise
                return self.registrar_interacao(conversa.id)

        conversa = self.registrar_interacao(conversa.id)
        if thread_id_foundry and conversa.thread_id_foundry != thread_id_foundry:
            conversa.thread_id_foundry = thread_id_foundry
            self._sessao.commit()
        return conversa

    def registrar_interacao(
        self, conversa_id: uuid.UUID, quando: datetime | None = None
    ) -> Conversa:
        """Atualiza a última interação, adiando o timeout da sessão.

        Chamado por `abrir_ou_continuar` (login/reabertura). A integração do
        chat (S12) deve chamar a cada mensagem recebida para que o job meça
        inatividade real, e não o tempo desde o login.
        """
        conversa = self.buscar_por_id(conversa_id)
        if conversa is None:
            raise ValueError(f"conversa {conversa_id} não encontrada")
        conversa.ultima_interacao = quando or datetime.now(timezone.utc)
        self._sessao.commit()
        return conversa

    def fechar_inativas(self, limite: datetime) -> list[Conversa]:
        """Fecha por TIMEOUT as sessões ABERTAS sem interação desde `limite`.

        O UPDATE é atômico (`WHERE status = 'ABERTA'`): um logout concorrente
        que fechou a sessão primeiro impede o job de sobrescrever o motivo
        `LOGOUT` por `TIMEOUT`. O `rowcount` diz quantas linhas foram
        realmente fechadas por esta chamada.
        """
        agora = datetime.now(timezone.utc)
        resultado = self._sessao.execute(
            update(Conversa)
            .where(
                Conversa.status == StatusConversa.ABERTA,
                Conversa.ultima_interacao < limite,
            )
            .values(
                status=StatusConversa.FECHADA,
                motivo_fechamento=MotivoFechamento.TIMEOUT,
                data_fim=agora,
            )
        )
        self._sessao.commit()
        if resultado.rowcount == 0:
            return []
        return list(
            self._sessao.scalars(
                select(Conversa).where(
                    Conversa.status == StatusConversa.FECHADA,
                    Conversa.motivo_fechamento == MotivoFechamento.TIMEOUT,
                    Conversa.data_fim == agora,
                )
            )
        )

    def listar(
        self,
        aluno_id: uuid.UUID | None = None,
        limite: int = LIMITE_LISTAGEM_PADRAO,
        offset: int = 0,
    ) -> list[Conversa]:
        """Lista sessões (mais recentes primeiro), opcionalmente por aluno."""
        consulta = select(Conversa).order_by(Conversa.data_inicio.desc())
        if aluno_id is not None:
            consulta = consulta.where(Conversa.aluno_id == aluno_id)
        consulta = consulta.limit(min(limite, LIMITE_LISTAGEM_MAXIMO)).offset(offset)
        return list(self._sessao.scalars(consulta))

    def fechar(self, conversa_id: uuid.UUID, motivo: MotivoFechamento) -> Conversa:
        """Fecha a conversa registrando motivo e data de fim.

        Lança `ValueError` se a conversa não existe ou já está fechada.
        """
        conversa = self.buscar_por_id(conversa_id)
        if conversa is None:
            raise ValueError(f"conversa {conversa_id} não encontrada")
        if conversa.status is StatusConversa.FECHADA:
            raise ValueError(f"conversa {conversa_id} já está fechada")
        self._marcar_fechada(conversa, motivo, datetime.now(timezone.utc))
        self._sessao.commit()
        return conversa

    def fechar_por_id_se_aberta(
        self, conversa_id: uuid.UUID, motivo: MotivoFechamento
    ) -> Conversa | None:
        """Fecha a conversa só se ainda estiver ABERTA; senão devolve `None`.

        Update atômico (`WHERE status = 'ABERTA'`): quem fechar primeiro vence.
        O logout usa isso para não falhar quando o job de timeout fechou a
        sessão na mesma hora.
        """
        agora = datetime.now(timezone.utc)
        resultado = self._sessao.execute(
            update(Conversa)
            .where(
                Conversa.id == conversa_id,
                Conversa.status == StatusConversa.ABERTA,
            )
            .values(
                status=StatusConversa.FECHADA,
                motivo_fechamento=motivo,
                data_fim=agora,
            )
        )
        self._sessao.commit()
        if resultado.rowcount == 0:
            return None
        return self.buscar_por_id(conversa_id)

    @staticmethod
    def _marcar_fechada(
        conversa: Conversa, motivo: MotivoFechamento, quando: datetime
    ) -> None:
        """Aplica status, motivo e data de fim (sem commit)."""
        conversa.status = StatusConversa.FECHADA
        conversa.motivo_fechamento = motivo
        conversa.data_fim = quando

    def buscar_por_id(self, conversa_id: uuid.UUID) -> Conversa | None:
        """Busca pelo id interno."""
        return self._sessao.get(Conversa, conversa_id)

    def buscar_por_id_por_aluno(self, aluno_id: uuid.UUID) -> Conversa | None:
        """Retorna a sessão mais recente do aluno, qualquer que seja o estado."""
        return self._sessao.scalars(
            select(Conversa)
            .where(Conversa.aluno_id == aluno_id)
            .order_by(Conversa.data_inicio.desc())
        ).first()

    def buscar_aberta_por_aluno(self, aluno_id: uuid.UUID) -> Conversa | None:
        """Retorna a conversa ABERTA do aluno, se existir.

        O índice único parcial garante no máximo uma ABERTA por aluno; o
        `first()` com ordenação decrescente é defensivo para bases antigas
        criadas antes da migração 0002.
        """
        return self._sessao.scalars(
            select(Conversa)
            .where(
                Conversa.aluno_id == aluno_id,
                Conversa.status == StatusConversa.ABERTA,
            )
            .order_by(Conversa.data_inicio.desc())
        ).first()
