from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, Boolean, ForeignKey, Integer, BigInteger, JSON, Identity
from backend.app.models.types import TZDateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=datetime.utcnow, nullable=False)

    users: Mapped[List["User"]] = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    warehouse_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    role: Mapped["Role"] = relationship("Role", back_populates="users")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    driver: Mapped[Optional["Driver"]] = relationship("Driver", back_populates="user", uselist=False)
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(start=1), primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=datetime.utcnow, nullable=False, index=True)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")
