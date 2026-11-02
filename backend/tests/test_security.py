"""Testes do hash de senha."""

from app.security import hash_senha, verificar_senha


def test_hash_confere_com_a_senha_original() -> None:
    senha_hash = hash_senha("admin123")

    assert senha_hash != "admin123"
    assert verificar_senha("admin123", senha_hash) is True


def test_hash_rejeita_senha_errada() -> None:
    senha_hash = hash_senha("admin123")

    assert verificar_senha("outra", senha_hash) is False


def test_hash_usa_salt_aleatorio() -> None:
    assert hash_senha("admin123") != hash_senha("admin123")
