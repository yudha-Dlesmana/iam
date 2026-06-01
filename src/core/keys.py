from pathlib import Path
from functools import lru_cache

from src.core.config import settings

# Keyset is read once at first access and cached for the process lifetime.
# Adding a new kid on disk (e.g. via scripts/gen_keys.sh) is NOT picked up
# automatically — call reload() or restart the app. Production rotation is
# expected to be scheduled (deploy new key, restart, then flip JWT_ACTIVE_KID
# on the next deploy), so the restart cost is acceptable.


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


def reload() -> None:
    """Invalidate the keyset cache so the next access re-reads from disk.

    Use after writing a new kid directory at runtime (operational tool / test).
    """
    _load.cache_clear()
