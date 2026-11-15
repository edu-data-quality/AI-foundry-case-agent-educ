"""Ciclo de vida da sessão do aluno no chat (issue #11).

- `timeout_minutos`: inatividade máxima antes do fechamento automático
  (`THREAD_TIMEOUT_MIN`, padrão 10).
- `fechar_conversas_inativas`: fecha por TIMEOUT as sessões ABERTAS sem
  interação no intervalo configurado.
- `loop_timeout_conversas`: job periódico iniciado no lifespan da API.

O conteúdo das mensagens não fica aqui: ele vive nos traces do Foundry. Este
módulo cuida apenas do registro E2E da sessão (início, fim e motivo).
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import int_env
from app.db.models import Conversa
from app.db.session import get_session
from app.repositories.conversas import ConversaRepository

logger = logging.getLogger(__name__)

TIMEOUT_PADRAO_MINUTOS = 10
INTERVALO_VERIFICACAO_PADRAO_SEGUNDOS = 60


def timeout_minutos() -> int:
    """Inatividade máxima da sessão em minutos (`THREAD_TIMEOUT_MIN`)."""
    return int_env("THREAD_TIMEOUT_MIN", TIMEOUT_PADRAO_MINUTOS)


def intervalo_verificacao_segundos() -> int:
    """Intervalo entre varreduras do job (`THREAD_TIMEOUT_CHECK_SEGUNDOS`)."""
    return int_env(
        "THREAD_TIMEOUT_CHECK_SEGUNDOS", INTERVALO_VERIFICACAO_PADRAO_SEGUNDOS
    )


def job_ativo() -> bool:
    """Liga/desliga o job neste processo (`THREAD_TIMEOUT_JOB_ATIVO`).

    Com mais de um worker (uvicorn/gunicorn), o job deve rodar em apenas um
    deles para não haver varreduras concorrentes. O operador liga a variável
    só no worker líder; os demais sobem com `THREAD_TIMEOUT_JOB_ATIVO=0`.
    """
    return os.getenv("THREAD_TIMEOUT_JOB_ATIVO", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def fechar_conversas_inativas(
    sessao: Session, agora: datetime | None = None
) -> list[Conversa]:
    """Fecha por TIMEOUT as sessões sem interação há mais de `timeout_minutos`."""
    agora = agora or datetime.now(timezone.utc)
    limite = agora - timedelta(minutes=timeout_minutos())
    return ConversaRepository(sessao).fechar_inativas(limite)


async def loop_timeout_conversas() -> None:
    """Varre as sessões inativas periodicamente até ser cancelado."""
    intervalo = intervalo_verificacao_segundos()
    while True:
        # Dorme primeiro: o startup não depende do banco estar pronto.
        await asyncio.sleep(intervalo)
        try:
            with get_session() as sessao:
                fechadas = fechar_conversas_inativas(sessao)
            if fechadas:
                logger.info("timeout: %d conversa(s) fechada(s)", len(fechadas))
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - o job não pode morrer por um erro
            logger.exception("falha ao fechar conversas inativas")
