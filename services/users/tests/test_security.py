"""Unit tests for the stdlib PBKDF2 password hashing helpers."""

from app.services.security import hash_password, verify_password


def test_hash_and_verify_roundtrip() -> None:
    password_hash = hash_password("S3cretPass!")
    assert password_hash.startswith("pbkdf2_sha256$")
    assert "S3cretPass!" not in password_hash
    assert verify_password("S3cretPass!", password_hash)


def test_verify_rejects_wrong_password() -> None:
    password_hash = hash_password("S3cretPass!")
    assert not verify_password("WrongPass!", password_hash)


def test_hash_is_salted_and_unique() -> None:
    assert hash_password("S3cretPass!") != hash_password("S3cretPass!")


def test_verify_rejects_malformed_hash() -> None:
    assert not verify_password("whatever", "not-a-valid-hash")


def test_verify_rejects_unknown_algorithm() -> None:
    assert not verify_password("whatever", "md5$1000$abcd$ef01")
