"""Emissão e validação de tokens JWT (issue #3: autenticação).

O token embute a identidade do usuário autenticado (`sub` = id do usuário,
`role`, `login`). Os endpoints de negócio devem filtrar os dados sempre a
partir do `sub`/`role` do token — nunca de um CPF ou id lido do corpo da
requisição. Isso garante a regra "o aluno só consulta os próprios dados".
"""

import os
from datetime import datetime, timedelta, timezone

import jwt

ALGORITMO = "HS256"
TIPO_TOKEN = "access"

# Mensagens de erro estáveis para as respostas HTTP (não vazar o motivo real).
ERRO_EXPIRADO = "token expirado"
ERRO_INVALIDO = "token inválido"


def _segredo() -> str:
    """Segredo de assinatura vindo do ambiente (obrigatório em produção)."""
    segredo = os.getenv("JWT_SECRET")
    if not segredo:
        raise RuntimeError(
            "JWT_SECRET não definido: configure a variável de ambiente "
            "para assinar os tokens de acesso."
        )
    if len(segredo.encode()) < 32:
        raise RuntimeError(
            "JWT_SECRET muito curto: use ao menos 32 bytes "
            "(recomendado 64) para assinatura HS256."
        )
    return segredo


def tempo_de_vida_minutos() -> int:
    """Tempo de vida do token em minutos (padrão 60)."""
    raw = os.getenv("JWT_EXPIRA_MINUTOS", "60")
    try:
        return max(1, int(raw))
    except ValueError:
        return 60


def criar_token(
    *,
    usuario_id: str,
    login: str,
    role: str,
    tempo_de_vida: timedelta | None = None,
) -> str:
    """Gera um JWT assinado com os claims de identidade do usuário."""
    agora = datetime.now(timezone.utc)
    expira = agora + (tempo_de_vida or timedelta(minutes=tempo_de_vida_minutos()))
    claims = {
        "sub": str(usuario_id),
        "login": login,
        "role": role,
        "type": TIPO_TOKEN,
        "iat": agora,
        "exp": expira,
    }
    return jwt.encode(claims, _segredo(), algorithm=ALGORITMO)


def decodificar_token(token: str) -> dict:
    """Valida assinatura e expiração; retorna os claims.

    Levanta `jwt.ExpiredSignatureError` quando o token passou do prazo e
    `jwt.InvalidTokenError` para token malformado ou de assinatura inválida.
    """
    return jwt.decode(token, _segredo(), algorithms=[ALGORITMO])