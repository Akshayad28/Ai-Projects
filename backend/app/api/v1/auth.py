"""User authentication router (registration, login, profile)."""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_authenticated_user
from app.core.rate_limit import rate_limit
from app.core.sanitizer import sanitize_text
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])

_PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128, description="Minimum 8 characters with letters and numbers")
    name: Optional[str] = Field(None, max_length=120)
    country: str = Field("IN", min_length=2, max_length=2)
    currency: str = Field("INR", min_length=3, max_length=3)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not _PASSWORD_PATTERN.match(v):
            raise ValueError("Password must be at least 8 characters long and contain both letters and numbers.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


@router.post(
    "/register",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60, bucket="auth_register"))],
)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Register a new user account with secure password hashing."""
    normalized_email = payload.email.lower().strip()

    # Check if user already exists
    existing = await db.execute(select(User).where(User.email == normalized_email))
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    # Sanitize metadata
    clean_name = sanitize_text(payload.name, max_length=120) if payload.name else None
    clean_country = sanitize_text(payload.country, max_length=2).upper()
    clean_currency = sanitize_text(payload.currency, max_length=3).upper()

    user = User(
        email=normalized_email,
        password_hash=hash_password(payload.password),
        name=clean_name,
        country=clean_country,
        currency=clean_currency,
        is_admin=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(data={"sub": user.id, "email": user.email, "is_admin": user.is_admin})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "country": user.country,
            "currency": user.currency,
            "is_admin": user.is_admin,
            "created_at": user.created_at.isoformat(),
        },
    }


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60, bucket="auth_login"))],
)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Authenticate user credentials and issue signed JWT."""
    normalized_email = payload.email.lower().strip()

    res = await db.execute(select(User).where(User.email == normalized_email))
    user = res.scalars().first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": user.id, "email": user.email, "is_admin": user.is_admin})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "country": user.country,
            "currency": user.currency,
            "is_admin": user.is_admin,
            "created_at": user.created_at.isoformat(),
        },
    }


@router.get("/me")
async def get_current_user_profile(user: User = Depends(require_authenticated_user)) -> Dict[str, Any]:
    """Retrieve profile of currently authenticated user."""
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "country": user.country,
        "currency": user.currency,
        "is_admin": user.is_admin,
        "use_personalization": user.use_personalization,
        "created_at": user.created_at.isoformat(),
    }
