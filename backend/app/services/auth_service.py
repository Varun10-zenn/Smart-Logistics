"""Authentication service."""
from datetime import timedelta
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    denylist,
)
from backend.app.models.user import User
from backend.app.schemas.auth import TokenResponse
from backend.app.schemas.user import UserRead


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Verify email + bcrypt password. Returns User ORM or None."""
    user = db.query(User).filter(User.email == email, User.is_active == True).first()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_tokens_for_user(user: User) -> TokenResponse:
    """Issue access + refresh JWT pair for a verified user."""
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.code,
    }
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def refresh_access_token(refresh_token: str) -> TokenResponse:
    """Validate refresh token and issue a new access token."""
    from fastapi import HTTPException, status

    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Invalid refresh token type.", "details": {}},
        )
    new_payload = {
        "sub": payload["sub"],
        "email": payload.get("email", ""),
        "role": payload.get("role", ""),
    }
    access_token = create_access_token(new_payload)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,  # refresh token unchanged
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def logout_token(jti: str, remaining_seconds: int) -> None:
    """Add a JTI to the denylist for the remaining token lifetime."""
    denylist.add(jti, ttl_seconds=max(remaining_seconds, 1))


def get_user_profile(db: Session, user: User) -> UserRead:
    """Build a UserRead from an ORM User (with role loaded)."""
    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role.code,
        is_active=user.is_active,
        created_at=user.created_at,
    )
