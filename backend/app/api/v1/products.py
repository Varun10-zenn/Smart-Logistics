from typing import Optional
from fastapi import APIRouter, Depends, status, UploadFile, File
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import require_role
from backend.app.schemas.common import Page
from backend.app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from backend.app.services import product_service

router = APIRouter(prefix="/products", tags=["Products"])

_READ_ROLES = ("admin", "warehouse_operator", "fleet_manager")
_ADMIN_ROLES = ("admin",)


@router.get("/import/template", response_class=PlainTextResponse)
def get_products_import_template():
    sample_csv = "sku,name,category,unit_weight_kg,unit_volume_cbm,price\nPROD-001,Smart Widget,Electronics,1.5,0.002,29.99\nPROD-002,Organic Milk,Grocery,1.0,0.001,4.50\n"
    return PlainTextResponse(content=sample_csv, media_type="text/csv")


@router.post("/import")
async def import_products(
    file: UploadFile = File(...),
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    content = (await file.read()).decode("utf-8")
    return product_service.import_products(db, content)


@router.get("", response_model=Page[ProductRead])
def list_products(
    page: int = 1, page_size: int = 20,
    category: Optional[str] = None, sku: Optional[str] = None,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return product_service.list_products(db, page, page_size, category, sku)


@router.post("", response_model=ProductRead, status_code=201)
def create_product(
    data: ProductCreate,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    return product_service.create_product(db, data)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: int,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return product_service.get_product(db, product_id)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int, data: ProductUpdate,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    return product_service.update_product(db, product_id, data)


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    product_service.delete_product(db, product_id)
