"""Password hashing with PBKDF2 (stdlib only, no extra dependency)."""

import hashlib
import hmac
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 120_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Hash a password with a random salt: ``pbkdf2_sha256$<iterations>$<salt>$<digest>``."""
    salt = secrets.token_hex(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITERATIONS)
    return f"{_ALGORITHM}${_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Check a password against a stored hash (constant-time comparison)."""
    try:
        algorithm, iterations_raw, salt, expected = password_hash.split("$")
        iterations = int(iterations_raw)
    except ValueError:
        return False
    if algorithm != _ALGORITHM:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), iterations)
    return hmac.compare_digest(digest.hex(), expected)
