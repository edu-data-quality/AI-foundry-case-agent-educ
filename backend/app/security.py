"""Hash de senhas com PBKDF2-SHA256 (stdlib, sem dependência extra)."""

import hashlib
import hmac
import os

ALGORITMO = "pbkdf2_sha256"
ITERACOES = 600_000  # piso atual do OWASP para PBKDF2-HMAC-SHA256
TAMANHO_SALT = 16


def hash_senha(senha: str) -> str:
    """Gera o hash com salt aleatório no formato `algoritmo$iteracoes$salt$hash`."""
    salt = os.urandom(TAMANHO_SALT)
    derivado = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt, ITERACOES)
    return f"{ALGORITMO}${ITERACOES}${salt.hex()}${derivado.hex()}"


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Confere a senha contra o hash armazenado, em tempo constante."""
    try:
        algoritmo, iteracoes, salt_hex, hash_hex = senha_hash.split("$")
        if algoritmo != ALGORITMO:
            return False
        derivado = hashlib.pbkdf2_hmac(
            "sha256", senha.encode(), bytes.fromhex(salt_hex), int(iteracoes)
        )
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(derivado.hex(), hash_hex)
