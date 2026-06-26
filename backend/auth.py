"""
auth.py
-------
Minimal auth: bcrypt-hashed passwords + random opaque session tokens
stored in the DB (not JWT — simpler to explain for this project's scope,
and we don't need stateless auth across multiple servers).
"""

import secrets
from passlib.hash import bcrypt


def hash_password(plain_password: str) -> str:
    return bcrypt.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.verify(plain_password, password_hash)


def generate_token() -> str:
    """32 bytes of randomness, hex-encoded -> 64 char opaque token."""
    return secrets.token_hex(32)
