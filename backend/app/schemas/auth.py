from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)


class RegisterResponse(BaseModel):
    user_id: str
    totp_secret: str
    provisioning_uri: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str = Field(min_length=6, max_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserSessionResponse(BaseModel):
    user_id: str
    email: EmailStr
    role: str
