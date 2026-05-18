from argon2 import PasswordHasher

_ph = PasswordHasher()


def hash_password(plain: str) -> str:
    return _ph.hash(plain)
