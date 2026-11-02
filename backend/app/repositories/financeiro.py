"""Repositório de mensalidades."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Mensalidade, StatusPagamento


class MensalidadeRepository:
    """Acesso aos boletos do aluno."""

    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def criar(
        self,
        *,
        aluno_id: uuid.UUID,
        mes_referencia: str,
        valor_original: Decimal,
        data_vencimento: date,
        status_pagamento: StatusPagamento = StatusPagamento.PENDENTE,
        linha_digitavel: str | None = None,
        qr_code_pix: str | None = None,
    ) -> Mensalidade:
        """Cria e persiste uma mensalidade."""
        mensalidade = Mensalidade(
            aluno_id=aluno_id,
            mes_referencia=mes_referencia,
            valor_original=valor_original,
            data_vencimento=data_vencimento,
            status_pagamento=status_pagamento,
            linha_digitavel=linha_digitavel,
            qr_code_pix=qr_code_pix,
        )
        self._sessao.add(mensalidade)
        self._sessao.commit()
        return mensalidade

    def listar_por_aluno(self, aluno_id: uuid.UUID) -> list[Mensalidade]:
        """Lista todas as mensalidades do aluno, da mais recente para a mais antiga."""
        return list(
            self._sessao.scalars(
                select(Mensalidade)
                .where(Mensalidade.aluno_id == aluno_id)
                .order_by(Mensalidade.mes_referencia.desc())
            )
        )

    def listar_em_aberto_por_aluno(self, aluno_id: uuid.UUID) -> list[Mensalidade]:
        """Lista boletos ainda não pagos (pendentes ou atrasados)."""
        return list(
            self._sessao.scalars(
                select(Mensalidade)
                .where(
                    Mensalidade.aluno_id == aluno_id,
                    Mensalidade.status_pagamento.in_(
                        [StatusPagamento.PENDENTE, StatusPagamento.ATRASADO]
                    ),
                )
                .order_by(Mensalidade.mes_referencia.desc())
            )
        )
