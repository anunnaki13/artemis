from fastapi import APIRouter, Depends, HTTPException, status
from pyotp import TOTP
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, new_totp_secret, verify_password, verify_totp
from app.db import get_session
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, RegisterResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_session)) -> RegisterResponse:
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
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    user = await session.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

    if user.totp_secret is None or not verify_totp(user.totp_secret, payload.totp_code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid totp code")

    return TokenResponse(access_token=create_access_token(str(user.id)))
