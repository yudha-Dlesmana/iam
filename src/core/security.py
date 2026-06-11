import uuid
import json
from datetime import datetime, timedelta, timezone
from typing import TypedDict, cast

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from redis.asyncio import Redis

from src.core.keys import active_private_key, public_key_for
from src.core.config import settings
from src.models.user import User

_ph = PasswordHasher()

ACCESS_ALGORITHM = "RS256"
REFRESH_ALGORITHM = "HS256"
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


def _audience_from(user: User) -> list[str]:
    perms = user.role.permission_name if user.role else []
    service = {p.split(".", 1)[0] for p in perms}
    return sorted(service) or [settings.JWT_ISSUER]


def _refresh_secret(kid: str) -> str:
    secret = settings.JWT_REFRESH_SECRETS.get(kid)
    if not secret:
        raise jwt.InvalidTokenError(f"unknown refresh kid: {kid}")
    return secret


class PayloadAccessToken(TypedDict):
    jti: str
    sub: str
    iss: str
    aud: list[str]
    iat: int
    exp: int
    email: str
    role: str
    permissions: list[str]


def create_access_token(user: User) -> str:
    payload: PayloadAccessToken = {
        "jti": str(uuid.uuid4()),
        "sub": user.id,
        "iss": settings.JWT_ISSUER,
        "aud": _audience_from(user),
        "iat": _now(),
        "exp": _now() + ACCESS_TTL,
        "email": user.email,
        "role": user.role_name,
        "permissions": user.role.permission_name if user.role else [],
    }
    private_key, kid = active_private_key()
    return jwt.encode(
        payload,
        private_key,
        algorithm=ACCESS_ALGORITHM,
        headers={"kid": kid},
    )


def decode_access_token(token: str) -> PayloadAccessToken:
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    if not kid:
        raise jwt.InvalidTokenError("missing kid")
    try:
        public_key = public_key_for(kid)
    except KeyError as e:
        raise jwt.InvalidTokenError("unknown kid") from e
    payload = jwt.decode(
        token,
        public_key,
        algorithms=[ACCESS_ALGORITHM],
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_ISSUER,
    )
    return cast(PayloadAccessToken, payload)


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
    kid = settings.JWT_ACTIVE_KID
    token = jwt.encode(
        payload, _refresh_secret(kid), algorithm=REFRESH_ALGORITHM, headers={"kid", kid}
    )
    return token, jti, device


def decode_refresh_token(token: str) -> PayloadRefreshToken:
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    if not kid:
        raise jwt.InvalidTokenError("missing refresh kid")
    return jwt.decode(
        token, settings.JWT_REFRESH_SECRET, algorithms=[REFRESH_ALGORITHM]
    )


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


async def get_session(r: Redis, user_id: str, device: str) -> dict | None:
    raw = await r.hget(f"sessions:{user_id}", device)
    if raw is None:
        return None
    data = json.loads(raw)
    data.pop("jti", None)
    data["device"] = device
    return data


async def list_sessions(r: Redis, user_id: str) -> list[dict]:
    raw = await r.hgetall(f"sessions:{user_id}")
    out = []
    for device, val in raw.items():
        data = json.loads(val)
        data.pop("jti", None)
        data["device"] = device
        out.append(data)
    return out
