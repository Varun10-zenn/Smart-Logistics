"""User management service."""
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import hash_password
from backend.app.models.user import User, Role
from backend.app.schemas.common import make_page
from backend.app.schemas.user import UserCreate, UserRead, UserUpdate


def _to_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role.code,
        warehouse_id=user.warehouse_id,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def list_users(db: Session, page: int = 1, page_size: int = 20):
    """Return paginated list of all users."""
    offset = (page - 1) * page_size
    total = db.query(User).count()
    users = db.query(User).order_by(User.created_at.desc()).offset(offset).limit(page_size).all()
    items = [_to_read(u) for u in users]
    return make_page(items, total, page, page_size)


def create_user(db: Session, data: UserCreate) -> UserRead:
    """Create a new user with hashed password."""
    if data.role_code == "warehouse_operator" and not data.warehouse_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "VALIDATION_ERROR", "message": "warehouse_id is required for warehouse_operator role", "details": {}},
        )
    if data.warehouse_id:
        from backend.app.models.warehouse import Warehouse
        wh = db.query(Warehouse).filter(Warehouse.id == data.warehouse_id).first()
        if not wh:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "VALIDATION_ERROR", "message": f"Warehouse #{data.warehouse_id} not found.", "details": {}},
            )

    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DUPLICATE_RESOURCE", "message": "Email already in use.", "details": {}},
        )
    role = db.query(Role).filter(Role.code == data.role_code).first()
    if role is None:
        role = Role(code=data.role_code, description=f"{data.role_code.capitalize()} Role")
        db.add(role)
        db.flush()
    user = User(
        email=data.email,
        full_name=data.full_name,
        phone=data.phone,
        password_hash=hash_password(data.password),
        role_id=role.id,
        warehouse_id=data.warehouse_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _to_read(user)


def get_user(db: Session, user_id: int) -> UserRead:
    """Get a single user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "User not found.", "details": {}},
        )
    return _to_read(user)


def update_user(db: Session, user_id: int, data: UserUpdate) -> UserRead:
    """Partial-update user fields."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "User not found.", "details": {}},
        )
    update_data = data.model_dump(exclude_unset=True)
    if "warehouse_id" in update_data and update_data["warehouse_id"] is not None:
        from backend.app.models.warehouse import Warehouse
        wh = db.query(Warehouse).filter(Warehouse.id == update_data["warehouse_id"]).first()
        if not wh:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "VALIDATION_ERROR", "message": f"Warehouse #{update_data['warehouse_id']} not found.", "details": {}},
            )
    for field, value in update_data.items():
        if field == "password":
            user.password_hash = hash_password(value)
        else:
            setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return _to_read(user)


def delete_user(db: Session, user_id: int) -> None:
    """Soft-delete: set is_active = False."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "User not found.", "details": {}},
        )
    user.is_active = False
    db.commit()
