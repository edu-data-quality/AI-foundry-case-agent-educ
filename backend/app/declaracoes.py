"""Geração do PDF e envio da declaração de matrícula (issue #6 / US1.2).

O PDF nasce do template HTML em `app/templates/declaracao_matricula.html`.
O envio usa a API do Resend via `requests` (mesma dependência já usada pelo
backend). Sem `RESEND_API_KEY`, o envio é **simulado**: o PDF é gerado e a
solicitação é registrada, mas nenhum e-mail sai — o modo dev fica explícito no
log e no `status` da resposta, sem mascarar a ausência da chave.
"""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from pathlib import Path

import requests
from fpdf import FPDF

LOGGER = logging.getLogger(__name__)

URL_RESEND = "https://api.resend.com/emails"
REMETENTE_PADRAO = "Assistente Acadêmico EAD <onboarding@resend.dev>"
NOME_ARQUIVO_PDF = "declaracao-matricula.pdf"
TEMPLATE = Path(__file__).with_name("templates") / "declaracao_matricula.html"
TIMEOUT_PADRAO_SEGUNDOS = 10


class ErroEnvioEmail(RuntimeError):
    """Falha no envio do e-mail pelo provedor (chave presente, envio falhou)."""


@dataclass(frozen=True)
class DadosDeclaracao:
    """Dados do aluno usados no PDF e no e-mail."""

    nome_completo: str
    cpf: str
    email: str
    curso: str | None = None
    polo: str | None = None


def formatar_cpf(cpf: str) -> str:
    """Formata `11144477735` como `111.444.777-35` (mantém formato desconhecido)."""
    digitos = "".join(caractere for caractere in cpf if caractere.isdigit())
    if len(digitos) != 11:
        return cpf
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


def _texto(valor: str | None, padrao: str = "não informado") -> str:
    """Escapa o valor para HTML e troca vazio/ausente por um texto neutro."""
    if valor is None or not valor.strip():
        return padrao
    return escape(valor.strip())


def _data_emissao(data: date | None = None) -> str:
    """Data no formato brasileiro (`dd/mm/aaaa`)."""
    return (data or datetime.now()).strftime("%d/%m/%Y")


def renderizar_html(dados: DadosDeclaracao, *, data: date | None = None) -> str:
    """Preenche o template HTML com os dados do aluno (valores escapados)."""
    return TEMPLATE.read_text(encoding="utf-8").format(
        nome_completo=_texto(dados.nome_completo),
        cpf=_texto(formatar_cpf(dados.cpf)),
        curso=_texto(dados.curso),
        polo=_texto(dados.polo),
        data_emissao=_data_emissao(data),
    )


def gerar_pdf_matricula(dados: DadosDeclaracao, *, data: date | None = None) -> bytes:
    """Compila o template HTML em PDF (A4) e devolve os bytes."""
    pdf = FPDF(format="A4")
    pdf.set_title("Declaração de Matrícula")
    pdf.set_author("Assistente Acadêmico EAD")
    pdf.set_margins(left=20, top=20, right=20)
    pdf.add_page()
    pdf.write_html(renderizar_html(dados, data=data))
    return bytes(pdf.output())


def _timeout_segundos() -> int:
    """Timeout HTTP do Resend em segundos (padrão 10)."""
    raw = os.getenv("RESEND_TIMEOUT_SEGUNDOS", str(TIMEOUT_PADRAO_SEGUNDOS))
    try:
        return max(1, int(raw))
    except ValueError:
        return TIMEOUT_PADRAO_SEGUNDOS


def _corpo_email(dados: DadosDeclaracao, *, data: date | None = None) -> str:
    """Versão HTML do e-mail (mesmo conteúdo do PDF)."""
    corpo = renderizar_html(dados, data=data)
    return (
        '<html><body style="font-family: Arial, sans-serif; font-size: 14px;">'
        f"{corpo}"
        "</body></html>"
    )


def enviar_email_declaracao(
    dados: DadosDeclaracao, pdf: bytes, *, data: date | None = None
) -> bool:
    """Envia a declaração pelo Resend.

    Retorna `True` quando o provedor aceitou o e-mail e `False` quando o envio
    foi simulado por falta de `RESEND_API_KEY` (modo dev). Falha real do
    provedor levanta `ErroEnvioEmail` — nunca é silenciada.
    """
    api_key = (os.getenv("RESEND_API_KEY") or "").strip()
    if not api_key:
        LOGGER.warning(
            "RESEND_API_KEY ausente: declaração de %s gerada, mas o envio "
            "para %s foi SIMULADO (modo dev).",
            dados.nome_completo,
            dados.email,
        )
        return False

    payload = {
        "from": os.getenv("RESEND_FROM", REMETENTE_PADRAO),
        "to": [dados.email],
        "subject": "Declaração de matrícula",
        "html": _corpo_email(dados, data=data),
        "attachments": [
            {
                "filename": NOME_ARQUIVO_PDF,
                "content": base64.b64encode(pdf).decode("ascii"),
            }
        ],
    }

    try:
        resposta = requests.post(
            URL_RESEND,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=_timeout_segundos(),
        )
        resposta.raise_for_status()
    except requests.HTTPError as exc:
        codigo = exc.response.status_code if exc.response is not None else "desconhecido"
        detalhe = exc.response.text[:200] if exc.response is not None else str(exc)
        raise ErroEnvioEmail(
            f"Resend respondeu {codigo}: {detalhe}"
        ) from exc
    except requests.RequestException as exc:
        raise ErroEnvioEmail(f"falha de comunicação com o Resend: {exc}") from exc

    return True
