"""
Core security module: JWT encoding/decoding, password hashing, token denylist,
and FastAPI authentication dependencies.
"""
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Set, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session, joinedload

from backend.app.core.config import settings
from backend.app.core.database import get_db

import bcrypt

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the given plaintext password."""
    pwd_bytes = plain.encode('utf-8')[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    try:
        pwd_bytes = plain.encode('utf-8')[:72]
        hashed_bytes = hashed.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# In-memory token denylist (JTI → expiry epoch)
# ---------------------------------------------------------------------------
class _InMemoryDenylist:
    """Thread-safe in-memory set for revoked JWT IDs (jti).

    Entries are stored with their expiry timestamp. A background sweep
    removes expired entries to prevent unbounded memory growth.
    """

    def __init__(self) -> None:
        self._store: Dict[str, float] = {}  # jti → expiry epoch (float)
        self._lock = threading.Lock()

    def add(self, jti: str, ttl_seconds: int) -> None:
        expiry = time.time() + ttl_seconds
        with self._lock:
            self._store[jti] = expiry
            self._evict_expired()

    def is_denied(self, jti: str) -> bool:
        with self._lock:
            expiry = self._store.get(jti)
            if expiry is None:
                return False
            if time.time() > expiry:
                del self._store[jti]
                return False
            return True

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [k for k, v in self._store.items() if v < now]
        for k in expired:
            del self._store[k]


denylist = _InMemoryDenylist()

# ---------------------------------------------------------------------------
# JWT helpers & Security Scheme
# ---------------------------------------------------------------------------
bearer_scheme = HTTPBearer(bearerFormat="JWT", auto_error=False)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = _utc_now() + (
        expires_delta if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    jti = str(uuid.uuid4())
    to_encode.update({
        "exp": expire,
        "iat": _utc_now(),
        "jti": jti,
        "type": "access",
    })
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a signed JWT refresh token."""
    to_encode = data.copy()
    expire = _utc_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    to_encode.update({
        "exp": expire,
        "iat": _utc_now(),
        "jti": jti,
        "type": "refresh",
    })
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Invalid or expired token.",
                "details": {},
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ---------------------------------------------------------------------------
# FastAPI Dependencies
# ---------------------------------------------------------------------------
def _get_dev_user(db: Session):
    """Helper to return an existing DB user or synthetic dev user for development mode bypass."""
    from backend.app.models.user import User, Role
    if db is not None:
        try:
            admin_role = db.query(Role).filter(Role.code == "admin").first()
            if admin_role:
                user = db.query(User).options(joinedload(User.role)).filter(User.role_id == admin_role.id, User.is_active == True).first()
                if user:
                    return user
            user = db.query(User).options(joinedload(User.role)).filter(User.is_active == True).first()
            if user:
                return user
        except Exception:
            pass
    dev_role = Role(id=1, code="admin", description="Development Admin Role")
    dev_user = User(
        id=1,
        email="dev@smartlogistics.com",
        full_name="Development Admin",
        is_active=True,
        role_id=1,
        role=dev_role
    )
    return dev_user


def _is_dev_bypass_active() -> bool:
    return bool(getattr(settings, "DEV_AUTH_BYPASS", False) and getattr(settings, "APP_ENV", "") == "local")


def _extract_token_str(auth_creds: Optional[HTTPAuthorizationCredentials]) -> str:
    if auth_creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Missing authentication token.", "details": {}},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_creds.credentials


def get_current_user(
    auth_creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """
    FastAPI dependency that decodes the JWT access token,
    checks the denylist, and returns the User ORM object.
    """
    from backend.app.models.user import User

    token = _extract_token_str(auth_creds)

    if _is_dev_bypass_active() and token == "dev-bypass-token":
        return _get_dev_user(db)

    payload = decode_token(token)

    # Verify token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Invalid token type.", "details": {}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check denylist
    jti = payload.get("jti", "")
    if denylist.is_denied(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Token has been revoked.", "details": {}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Token payload missing subject.", "details": {}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).options(joinedload(User.role)).filter(User.id == int(user_id_str), User.is_active == True).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "User not found or inactive.", "details": {}},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user_from_db(
    auth_creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(None),  # placeholder — see require_role below
):
    """Thin wrapper used by routers that already inject db via Depends(get_db)."""
    pass


class _RoleDependency:
    """Callable dependency class for role enforcement."""

    def __init__(self, *allowed_roles: str):
        self.allowed_roles = set(allowed_roles)

    def __call__(
        self,
        auth_creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
        db: Session = Depends(get_db)
    ):
        from backend.app.models.user import User

        token = _extract_token_str(auth_creds)

        if _is_dev_bypass_active() and token == "dev-bypass-token":
            return _get_dev_user(db)

        payload = decode_token(token)

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHORIZED", "message": "Invalid token type.", "details": {}},
            )

        jti = payload.get("jti", "")
        if denylist.is_denied(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHORIZED", "message": "Token revoked.", "details": {}},
            )

        role_code = payload.get("role", "")
        user_id_str = payload.get("sub")

        if role_code not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": f"Role '{role_code}' is not allowed to access this resource.",
                    "details": {"required_roles": list(self.allowed_roles)},
                },
            )

        user = db.query(User).options(joinedload(User.role)).filter(User.id == int(user_id_str), User.is_active == True).first()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHORIZED", "message": "User not found or inactive.", "details": {}},
            )
        return user


def require_role(*roles: str) -> _RoleDependency:
    """Return a FastAPI dependency that enforces the given role codes.

    Usage in router:
        current_user: User = Depends(require_role("admin", "fleet_manager"))
    """
    return _RoleDependency(*roles)
