import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from redis.asyncio import Redis

from src.core.config import settings
from src.models.user import User

_ph = PasswordHasher()

ALGORITHM = "HS256"
ACCESS_TTL = timedelta(minutes=15)
REFRESH_TTL = timedelta(days=7)


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(hashed: str, plain: str) -> bool:
    try:
        return _ph.verify(hash=hashed, password=plain)
    except VerifyMismatchError:
        return False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user: User) -> str:
    payload = {
        "jti": str(uuid.uuid4()),
        "sub": user.id,
        "iat": _now(),
        "exp": _now() + ACCESS_TTL,
        "email": user.email,
        "role": user.role_name,
    }
    return jwt.encode(payload, settings.JWT_ACCESS_SECRET, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_ACCESS_SECRET, algorithms=[ALGORITHM])


def create_refresh_token(user_id: str, fam: str | None = None) -> tuple[str, str, str]:
    jti = str(uuid.uuid4())
    fam = fam or str(uuid.uuid4())
    payload = {
        "jti": jti,
        "sub": user_id,
        "iat": _now(),
        "exp": _now() + REFRESH_TTL,
        "fam": fam,
    }
    token = jwt.encode(payload, settings.JWT_REFRESH_SECRET, algorithm=ALGORITHM)
    return token, jti, fam


def decode_refresh_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_REFRESH_SECRET, algorithms=[ALGORITHM])


async def store_refresh(r: Redis, jti: str, fam: str, sub: str):
    ttl = int(REFRESH_TTL.total_seconds())
    pipe = r.pipeline()
    pipe.hset(f"refresh:{jti}", mapping={"sub": sub, "fam": fam, "used": "0"})
    pipe.expire(f"refresh:{jti}", ttl)
    pipe.sadd(f"fam:{fam}", jti)
    pipe.expire(f"fam:{fam}", ttl)
    await pipe.execute()


_CONSUME_LUA = """
local used = redis.call('HGET', KEYS[1], 'used')
if used == false then
    return {'MISSING'}
end
if used == '1' then
    return {'REUSE', redis.call('HGET', KEYS[1], 'fam')}
end
redis.call('HSET', KEYS[1], 'used', '1')
return {"OK", redis.call('HGET', KEYS[1], 'sub'), redis.call('HGET', KEYS[1], 'fam')}
"""


async def consume_refresh(r: Redis, jti: str) -> dict | None:
    res = await r.eval(_CONSUME_LUA, 1, f"refresh:{jti}")
    status = res[0]
    if status == "MISSING":
        return None
    if status == "REUSE":
        await revoke_family(r, res[1])
        return None
    return {"sub": res[1], "fam": res[2]}


async def revoke_refresh(r: Redis, jti: str) -> None:
    await r.delete(f"refresh:{jti}")


async def revoke_family(r: Redis, fam: str) -> None:
    jtis = await r.smembers(f"fam:{fam}")
    pipe = r.pipeline()
    for j in jtis:
        pipe.delete(f"refresh:{j}")
    pipe.delete(f"fam:{fam}")
    await pipe.execute()
