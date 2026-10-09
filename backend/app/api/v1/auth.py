"""Auth router."""
import time
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, decode_token, denylist
from backend.app.core.config import settings
from backend.app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, SignupRequest, RegisterRequest
from backend.app.schemas.user import UserRead, UserCreate
from backend.app.services import auth_service
from backend.app.services import audit_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=UserRead, status_code=201, summary="Register a new staff user")
def signup(data: SignupRequest, request: Request, db: Session = Depends(get_db)):
    from backend.app.services.user_service import create_user
    user_data = UserCreate(
        email=data.email,
        password=data.password,
        full_name=data.full_name,
        role_code="fleet_manager",
    )
    
    user = create_user(db, user_data)
    audit_service.log_action(
        db, user_id=user.id, action="SIGNUP_SUCCESS",
        resource_type="users", resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )
    return user


@router.post("/register", response_model=UserRead, status_code=201, summary="Register a new customer account")
def register_customer(data: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    from backend.app.services.user_service import create_user
    full_name = data.username or data.email.split("@")[0]
    user_data = UserCreate(
        email=data.email,
        password=data.password,
        full_name=full_name,
        role_code="customer",
    )
    user = create_user(db, user_data)
    audit_service.log_action(
        db, user_id=user.id, action="CUSTOMER_REGISTER_SUCCESS",
        resource_type="users", resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )
    return user


@router.post("/login", response_model=TokenResponse, summary="Login and receive JWT tokens")
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(db, data.email, data.password)
    if user is None:
        audit_service.log_action(
            db, user_id=None, action="LOGIN_FAILED",
            resource_type="users", details={"email": data.email},
            ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Invalid email or password.", "details": {}},
        )
    tokens = auth_service.create_tokens_for_user(user)
    audit_service.log_action(
        db, user_id=user.id, action="LOGIN_SUCCESS",
        resource_type="users", resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )
    return tokens


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
def refresh(data: RefreshRequest):
    return auth_service.refresh_access_token(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Logout and revoke token")
def logout(
    request: Request,
    token: str = Depends(lambda r=None: None),  # will be extracted manually
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        raw_token = auth_header[7:]
        try:
            payload = decode_token(raw_token)
            jti = payload.get("jti", "")
            exp = payload.get("exp", 0)
            remaining = max(0, int(exp - time.time()))
            auth_service.logout_token(jti, remaining)
        except Exception:
            pass
    audit_service.log_action(
        db, user_id=current_user.id, action="LOGOUT",
        resource_type="users", resource_id=str(current_user.id),
        ip_address=request.client.host if request.client else None,
    )


@router.get("/me", response_model=UserRead, summary="Get current user profile")
def me(current_user=Depends(get_current_user)):
    return UserRead(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        role=current_user.role.code,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )
