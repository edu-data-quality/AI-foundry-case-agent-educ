import re

from pydantic import ValidationError

from triagem.schemas import EntradaAluno

PADROES_SUSPEITOS = re.compile(
    r"(ignore\s+(as\s+)?instru\w*|desconsidere\s+as\s+instru\w*|system\s*prompt|"
    r"drop\s+table|<script|revele\s+(o\s+)?prompt)",
    re.IGNORECASE,
)


class EntradaInvalida(Exception):
    pass


def sanitizar_texto(texto: str) -> str:
    texto = " ".join(texto.split())
    texto = PADROES_SUSPEITOS.sub("[conteudo-removido]", texto)
    return texto


def validar_entrada(aluno_id: str, texto: str) -> EntradaAluno:
    texto_limpo = sanitizar_texto(texto or "")
    try:
        return EntradaAluno(aluno_id=(aluno_id or "").strip(), texto=texto_limpo)
    except ValidationError as exc:
        raise EntradaInvalida(f"Entrada inválida: {exc.errors()}") from exc
