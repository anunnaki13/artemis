from fastapi import APIRouter, Depends, HTTPException, Request, status
from pyotp import TOTP
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import check_rate_limit, client_ip
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    new_totp_secret,
    verify_password,
    verify_totp,
)
from app.core.sessions import revoke_access_session, store_access_session
from app.db import get_session
from app.deps import get_current_user
from app.models import User
from app.redis import get_redis
from app.schemas.auth import LoginRequest, RegisterRequest, RegisterResponse, TokenResponse, UserSessionResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> RegisterResponse:
    ip_address = client_ip(request)
    await check_rate_limit(
        redis,
        f"aiq:rate:auth:register:{ip_address}",
        limit=5,
        window_seconds=3600,
    )
    existing = await session.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")

    secret = new_totp_secret()
    user = User(email=str(payload.email), password_hash=hash_password(payload.password), totp_secret=secret)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return RegisterResponse(
        user_id=str(user.id),
        totp_secret=secret,
        provisioning_uri=TOTP(secret).provisioning_uri(name=user.email, issuer_name="AIQ-BOT"),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    ip_address = client_ip(request)
    await check_rate_limit(
        redis,
        f"aiq:rate:auth:login:ip:{ip_address}",
        limit=10,
        window_seconds=3600,
    )
    await check_rate_limit(
        redis,
        f"aiq:rate:auth:login:email:{payload.email}",
        limit=10,
        window_seconds=3600,
    )
    user = await session.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

    if user.totp_secret is None or not verify_totp(user.totp_secret, payload.totp_code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid totp code")

    access_token = create_access_token(str(user.id))
    await store_access_session(redis, decode_access_token(access_token))
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserSessionResponse)
async def me(user: User = Depends(get_current_user)) -> UserSessionResponse:
    return UserSessionResponse(user_id=str(user.id), email=user.email, role=user.role)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    redis: Redis = Depends(get_redis),
) -> None:
    auth_header = request.headers.get("authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return
    try:
        payload = decode_access_token(token)
    except Exception:
        return
    await revoke_access_session(redis, payload)
