"""Leitura de configuração do ambiente.

Centraliza o parse de variáveis numéricas para não repetir `try/except
ValueError` em cada módulo (timeout do Resend, timeout das sessões etc.).
"""

import os


def int_env(variavel: str, padrao: int, *, minimo: int = 1) -> int:
    """Lê um inteiro do ambiente; usa `padrao` se ausente ou inválido.

    O valor nunca fica abaixo de `minimo` (evita timeout zero/negativo).
    """
    raw = os.getenv(variavel, str(padrao))
    try:
        return max(minimo, int(raw))
    except ValueError:
        return padrao


def lista_env(variavel: str, padrao: list[str]) -> list[str]:
    """Lê uma lista separada por vírgulas; usa `padrao` se ausente/vazia.

    Itens vazios e espaços em volta são descartados
    (ex: `CORS_ORIGINS="http://a, http://b,"`).
    """
    raw = os.getenv(variavel)
    if raw is None or not raw.strip():
        return padrao
    return [item.strip() for item in raw.split(",") if item.strip()]
