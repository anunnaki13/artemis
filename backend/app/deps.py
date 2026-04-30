from uuid import UUID

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import decode_access_token
from app.core.sessions import is_access_session_active
from app.db import get_session
from app.models import User
from app.redis import get_redis

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    access_cookie: str | None = Cookie(default=None, alias=get_settings().auth_cookie_name),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> User:
    token = access_cookie
    if credentials is not None and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing session")
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc

    if not await is_access_session_active(redis, payload):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="inactive session")

    user = await session.get(User, UUID(str(payload["sub"])))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
    return user
