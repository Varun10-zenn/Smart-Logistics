from typing import Optional
from fastapi import APIRouter, Depends, status, UploadFile, File
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import require_role
from backend.app.schemas.common import Page
from backend.app.schemas.inventory import InventoryCreate, InventoryRead, InventoryUpdate
from backend.app.services import inventory_service

router = APIRouter(prefix="/inventory", tags=["Inventory"])

_READ_ROLES = ("admin", "warehouse_operator", "fleet_manager")
_WRITE_ROLES = ("admin", "warehouse_operator")


@router.get("/import/template", response_class=PlainTextResponse)
def get_inventory_import_template():
    sample_csv = "warehouse_code,location_code,sku,quantity,reorder_threshold\nWH-001,A1-S01,PROD-001,100,10\nWH-001,A1-S02,PROD-002,50,5\n"
    return PlainTextResponse(content=sample_csv, media_type="text/csv")


@router.post("/import")
async def import_inventory(
    file: UploadFile = File(...),
    current_user=Depends(require_role(*_WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    content = (await file.read()).decode("utf-8")
    return inventory_service.import_inventory(db, content)


@router.get("", response_model=Page[InventoryRead])
def list_inventory(
    page: int = 1, page_size: int = 20,
    warehouse_id: Optional[int] = None, product_id: Optional[int] = None,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return inventory_service.list_inventory(db, page, page_size, warehouse_id, product_id)


@router.post("", response_model=InventoryRead, status_code=201)
def upsert_inventory(
    data: InventoryCreate,
    current_user=Depends(require_role(*_WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    return inventory_service.upsert_inventory(db, data)


@router.get("/{inventory_id}", response_model=InventoryRead)
def get_inventory(
    inventory_id: int,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return inventory_service.get_inventory(db, inventory_id)


@router.patch("/{inventory_id}", response_model=InventoryRead)
def update_inventory(
    inventory_id: int, data: InventoryUpdate,
    current_user=Depends(require_role(*_WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    return inventory_service.update_inventory(db, inventory_id, data)


@router.delete("/{inventory_id}", status_code=204)
def delete_inventory(
    inventory_id: int,
    current_user=Depends(require_role(*_WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    inventory_service.delete_inventory(db, inventory_id)
