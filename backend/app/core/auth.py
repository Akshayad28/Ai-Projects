"""Authentication and authorization dependencies."""
from __future__ import annotations

import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_db

# HTTPBearer scheme that doesn't automatically error so we can support optional tokens
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Retrieve authenticated user from JWT token if present, otherwise None."""
    if not credentials or not credentials.credentials:
        return None

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        return None

    user_id = str(payload["sub"])
    res = await db.execute(select(User).where(User.id == user_id))
    return res.scalars().first()


async def require_authenticated_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Strictly require a valid authenticated user. Raises 401 if missing or invalid."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = str(payload["sub"])
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with this token was not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_admin(
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    user: Optional[User] = Depends(get_current_user_optional),
) -> bool:
    """Protect admin routes.
    Accepts either:
    1. A valid X-Admin-Key matching settings.admin_api_token, or
    2. A valid JWT from a User with is_admin=True.
    Raises 401 or 403 if unauthorized.
    """
    settings = get_settings()

    # 1. Check admin key if configured
    if settings.admin_api_token and x_admin_key:
        if secrets.compare_digest(x_admin_key.strip(), settings.admin_api_token.strip()):
            return True

    # 2. Check user role
    if user and user.is_admin:
        return True

    # If neither matched
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access forbidden. Valid admin token or X-Admin-Key header required.",
    )
