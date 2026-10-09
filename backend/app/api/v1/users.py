"""Users router — admin only with own-record exceptions for driver."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role
from backend.app.schemas.common import Page
from backend.app.schemas.user import UserCreate, UserRead, UserUpdate
from backend.app.services import user_service, audit_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=Page[UserRead], summary="List all users (admin only)")
def list_users(
    page: int = 1, page_size: int = 20,
    current_user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return user_service.list_users(db, page, page_size)


@router.post("", response_model=UserRead, status_code=201, summary="Create user (admin only)")
def create_user(
    data: UserCreate, request: Request,
    current_user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    result = user_service.create_user(db, data)
    audit_service.log_action(
        db, user_id=current_user.id, action="CREATE_USER",
        resource_type="users", resource_id=str(result.id),
        ip_address=request.client.host if request.client else None,
    )
    return result


@router.get("/{user_id}", response_model=UserRead, summary="Get user by ID (admin or own)")
def get_user(
    user_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Admin sees any user; others can only see themselves
    role = current_user.role.code
    if role != "admin" and current_user.id != user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    return user_service.get_user(db, user_id)


@router.patch("/{user_id}", response_model=UserRead, summary="Update user (admin or own)")
def update_user(
    user_id: int, data: UserUpdate, request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.role.code
    if role != "admin" and current_user.id != user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Access denied.", "details": {}})
    # Non-admins cannot change is_active
    if role != "admin" and data.is_active is not None:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Only admins can change active status.", "details": {}})
    result = user_service.update_user(db, user_id, data)
    audit_service.log_action(
        db, user_id=current_user.id, action="UPDATE_USER",
        resource_type="users", resource_id=str(user_id),
        ip_address=request.client.host if request.client else None,
    )
    return result


@router.delete("/{user_id}", status_code=204, summary="Soft-delete user (admin only)")
def delete_user(
    user_id: int, request: Request,
    current_user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    user_service.delete_user(db, user_id)
    audit_service.log_action(
        db, user_id=current_user.id, action="DELETE_USER",
        resource_type="users", resource_id=str(user_id),
        ip_address=request.client.host if request.client else None,
    )
