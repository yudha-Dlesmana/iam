from pathlib import Path
from functools import lru_cache

from src.core.config import settings


@lru_cache
def _load() -> tuple[dict[str, str], dict[str, str]]:
    """Return (private_by_kid, public_by_kid)."""
    base = Path(settings.JWT_KEYS_DIR)
    private: dict[str, str] = {}
    public: dict[str, str] = {}
    for d in base.iterdir():
        if not d.is_dir():
            continue
        kid = d.name
        private[kid] = (d / "private.pem").read_text()
        public[kid] = (d / "public.pem").read_text()
    if settings.JWT_ACTIVE_KID not in private:
        raise RuntimeError(f"active kid '{settings.JWT_ACTIVE_KID}'")
    return private, public


def active_private_key() -> tuple[str, str]:
    private, _ = _load()
    kid = settings.JWT_ACTIVE_KID
    return private[kid], kid


def public_key_for(kid: str) -> str:
    _, public = _load()
    if kid not in public:
        raise KeyError(f"unknown kid: {kid}")
    return public[kid]


def all_public_keys() -> dict[str, str]:
    _, public = _load()
    return public
