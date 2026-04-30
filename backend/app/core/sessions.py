from datetime import datetime, timezone
from typing import Any

from redis.asyncio import Redis

SESSION_PREFIX = "aiq:session"


def _session_key(jti: str) -> str:
    return f"{SESSION_PREFIX}:{jti}"


def token_ttl_seconds(payload: dict[str, Any]) -> int:
    exp = payload.get("exp")
    if not isinstance(exp, int):
        return 0
    now = int(datetime.now(timezone.utc).timestamp())
    return max(exp - now, 0)


async def store_access_session(redis: Redis, payload: dict[str, Any]) -> None:
    ttl = token_ttl_seconds(payload)
    if ttl <= 0:
        return
    await redis.setex(_session_key(str(payload["jti"])), ttl, str(payload["sub"]))


async def is_access_session_active(redis: Redis, payload: dict[str, Any]) -> bool:
    subject = await redis.get(_session_key(str(payload["jti"])))
    return bool(subject == payload["sub"])


async def revoke_access_session(redis: Redis, payload: dict[str, Any]) -> None:
    await redis.delete(_session_key(str(payload["jti"])))
