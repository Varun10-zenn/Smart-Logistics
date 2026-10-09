"""Driver service."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models.delivery import Driver
from backend.app.models.user import User
from backend.app.schemas.common import make_page
from backend.app.schemas.driver import DriverCreate, DriverRead, DriverUpdate


def _to_read(driver: Driver) -> DriverRead:
    full_name = ""
    if driver.user:
        full_name = driver.user.full_name
    return DriverRead(
        id=driver.id,
        user_id=driver.user_id,
        full_name=full_name,
        license_number=driver.license_number,
        status=driver.status,
        rating=float(driver.rating),
    )


def list_drivers(db: Session, page: int = 1, page_size: int = 20,
                 status: str = None):
    q = db.query(Driver)
    if status:
        q = q.filter(Driver.status == status)
    total = q.count()
    drivers = q.offset((page - 1) * page_size).limit(page_size).all()
    return make_page([_to_read(d) for d in drivers], total, page, page_size)


def create_driver(db: Session, data: DriverCreate) -> DriverRead:
    user = db.query(User).filter(User.id == data.user_id, User.is_active == True).first()
    if user is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "User not found.", "details": {}})
    existing = db.query(Driver).filter(Driver.user_id == data.user_id).first()
    if existing:
        raise HTTPException(status_code=409, detail={"code": "DUPLICATE_RESOURCE", "message": "Driver profile already exists for this user.", "details": {}})
    dup_license = db.query(Driver).filter(Driver.license_number == data.license_number).first()
    if dup_license:
        raise HTTPException(status_code=409, detail={"code": "DUPLICATE_RESOURCE", "message": "License number already registered.", "details": {}})
    driver = Driver(
        user_id=data.user_id,
        license_number=data.license_number,
        status="available",
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return _to_read(driver)


def get_driver(db: Session, driver_id: int) -> DriverRead:
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if driver is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Driver not found.", "details": {}})
    return _to_read(driver)


def update_driver(db: Session, driver_id: int, data: DriverUpdate) -> DriverRead:
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if driver is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Driver not found.", "details": {}})
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(driver, field, value)
    db.commit()
    db.refresh(driver)
    return _to_read(driver)
