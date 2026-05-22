import uuid
import json
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


def create_refresh_token(
    user_id: str, device: str | None = None
) -> tuple[str, str, str]:
    jti = str(uuid.uuid4())
    device = device or str(uuid.uuid4())
    payload = {
        "jti": jti,
        "sub": user_id,
        "device": device,
        "iat": _now(),
        "exp": _now() + REFRESH_TTL,
    }
    token = jwt.encode(payload, settings.JWT_REFRESH_SECRET, algorithm=ALGORITHM)
    return token, jti, device


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


async def store_session(
    r: Redis, user_id: str, device: str, jti: str, ip: str, ua: str
) -> None:
    ttl = int(REFRESH_TTL.total_seconds())
    now = _now().isoformat()
    val = json.dumps(
        {"jti": jti, "ip": ip, "ua": ua, "created_at": now, "last_seen": now}
    )
    pipe = r.pipeline()
    pipe.hset(f"sessions:{user_id}", device, val)
    pipe.expire(f"sessions:{user_id}", ttl)
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
    sub, fam = res[1], res[2]
    return {"sub": sub, "fam": fam}


_ROTATE_LUA = """
local cur = redis.call('HGET', KEYS[1], ARGV[1])
if cur == false then
    return {'MISSING'}
end
local data = cjson.decode(cur)
if data['jti'] ~= ARGV[2] then
    return {'REUSE'}
end
data['jti'] = ARGV[3]
data['ip'] = ARGV[4]
data['last_seen'] = ARGV[5]
redis.call('HSET', KEYS[1], ARGV[1], cjson.encode(data))
return {'OK'}
"""


async def rotate_session(
    r: Redis, user_id: str, device: str, old_jti: str, new_jti: str, ip: str
) -> str:
    now = _now().isoformat()
    res = await r.eval(
        _ROTATE_LUA, 1, f"sessions:{user_id}", device, old_jti, new_jti, ip, now
    )
    return res[0]


async def revoke_refresh(r: Redis, jti: str) -> None:
    fam = await r.hget(f"refresh:{jti}", "fam")
    pipe = r.pipeline()
    pipe.delete(f"refresh:{jti}")
    if fam:
        pipe.srem(f"fam:{fam}", jti)
    await pipe.execute()


async def revoke_device(r: Redis, user_id: str, device: str) -> None:
    await r.hdel(f"sessions:{user_id}", device)


async def revoke_family(r: Redis, fam: str) -> None:
    jtis = await r.smembers(f"fam:{fam}")
    pipe = r.pipeline()
    for j in jtis:
        pipe.delete(f"refresh:{j}")
    pipe.delete(f"fam:{fam}")
    await pipe.execute()


async def revoke_user(r: Redis, user_id: str) -> None:
    await r.delete(f"sessions:{user_id}")


async def list_sessions(r: Redis, user_id: str) -> list[dict]:
    raw = await r.hgetall(f"sessions:{user_id}")
    out = []
    for device, val in raw.items():
        data = json.load(val)
        data.pop("jti", None)
        data["device"] = device
        out.append(data)
    return out
