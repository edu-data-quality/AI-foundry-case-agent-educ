"""Testes do repositório de mensalidades."""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import StatusPagamento
from app.repositories.alunos import AlunoRepository
from app.repositories.financeiro import MensalidadeRepository


def _aluno(sessao: Session):
    return AlunoRepository(sessao).criar(
        cpf="12345678901", nome_completo="Maria Souza", email="maria@exemplo.com"
    )


def test_cria_mensalidade_pendente_com_valor_decimal(sessao: Session) -> None:
    aluno = _aluno(sessao)

    mensalidade = MensalidadeRepository(sessao).criar(
        aluno_id=aluno.id,
        mes_referencia="2026-11",
        valor_original=Decimal("450.00"),
        data_vencimento=date(2026, 11, 10),
        linha_digitavel="23793.38128 60007.827136 95000.063305 9 00000000045000",
        qr_code_pix="00020126pix-simulado",
    )

    assert mensalidade.status_pagamento is StatusPagamento.PENDENTE
    assert mensalidade.valor_original == Decimal("450.00")


def test_lista_boletos_em_aberto_ignora_pagos(sessao: Session) -> None:
    aluno = _aluno(sessao)
    repo = MensalidadeRepository(sessao)
    pendente = repo.criar(
        aluno_id=aluno.id,
        mes_referencia="2026-11",
        valor_original=Decimal("450.00"),
        data_vencimento=date(2026, 11, 10),
    )
    pago = repo.criar(
        aluno_id=aluno.id,
        mes_referencia="2026-10",
        valor_original=Decimal("450.00"),
        data_vencimento=date(2026, 10, 10),
        status_pagamento=StatusPagamento.PAGO,
    )

    em_aberto = repo.listar_em_aberto_por_aluno(aluno.id)

    assert [mensalidade.id for mensalidade in em_aberto] == [pendente.id]
    assert pago.id not in {mensalidade.id for mensalidade in em_aberto}
