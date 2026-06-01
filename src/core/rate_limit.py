from redis.asyncio import Redis

_SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local cutoff = now - window

redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
local count = redis.call('ZCARD', key)

if count >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = window - (now - tonumber(oldest[2]))
    if retry_after < 1 then retry_after = 1 end
    return {0, retry_after}
end

redis.call('ZADD', key, now, now .. ':' .. count)
redis.call('EXPIRE', key, window)
return {1, 0}
"""


async def hit(r: Redis, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Sliding-window rate limit hit.

    Returns (allowed, retry_after_seconds). retry_after is 0 when allowed.
    """
    now_ms = await r.time()
    now = now_ms[0]
    res = await r.eval(
        _SLIDING_WINDOW_LUA, 1, f"ratelimit:{key}", now, window_seconds, limit
    )
    allowed = bool(res[0])
    return allowed, int(res[1])


async def reset(r: Redis, key: str) -> None:
    await r.delete(f"ratelimit:{key}")
