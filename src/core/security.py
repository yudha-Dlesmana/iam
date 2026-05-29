import uuid
import json
from datetime import datetime, timedelta, timezone
from typing import TypedDict

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


class PayloadAccessToken(TypedDict):
    jti: str
    sub: str
    iat: int
    exp: int
    email: str
    role: str
    permissions: list[str]


def create_access_token(user: User) -> str:
    payload: PayloadAccessToken = {
        "jti": str(uuid.uuid4()),
        "sub": user.id,
        "iat": _now(),
        "exp": _now() + ACCESS_TTL,
        "email": user.email,
        "role": user.role_name,
        "permissions": user.role.permission_name,
    }
    return jwt.encode(payload, settings.JWT_ACCESS_SECRET, algorithm=ALGORITHM)


def decode_access_token(token: str) -> PayloadAccessToken:
    return jwt.decode(token, settings.JWT_ACCESS_SECRET, algorithms=[ALGORITHM])


class PayloadRefreshToken(TypedDict):
    jti: str
    sub: str
    device: str
    iat: int
    exp: int


def create_refresh_token(
    user_id: str, device: str | None = None
) -> tuple[str, str, str]:
    jti = str(uuid.uuid4())
    device = device or str(uuid.uuid4())
    payload: PayloadRefreshToken = {
        "jti": jti,
        "sub": user_id,
        "device": device,
        "iat": _now(),
        "exp": _now() + REFRESH_TTL,
    }
    token = jwt.encode(payload, settings.JWT_REFRESH_SECRET, algorithm=ALGORITHM)
    return token, jti, device


def decode_refresh_token(token: str) -> PayloadRefreshToken:
    return jwt.decode(token, settings.JWT_REFRESH_SECRET, algorithms=[ALGORITHM])


async def peek_session(r: Redis, user_id: str, device: str, jti: str) -> bool:
    cur = await r.hget(f"sessions:{user_id}", device)
    if cur is None:
        return False
    return json.loads(cur)["jti"] == jti


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


async def revoke_device(r: Redis, user_id: str, device: str) -> None:
    await r.hdel(f"sessions:{user_id}", device)


async def revoke_user(r: Redis, user_id: str) -> None:
    await r.delete(f"sessions:{user_id}")


async def list_sessions(r: Redis, user_id: str) -> list[dict]:
    raw = await r.hgetall(f"sessions:{user_id}")
    out = []
    for device, val in raw.items():
        data = json.loads(val)
        data.pop("jti", None)
        data["device"] = device
        out.append(data)
    return out
