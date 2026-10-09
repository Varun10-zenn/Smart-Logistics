"""Product service."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models.warehouse import Product
from backend.app.schemas.common import make_page
from backend.app.schemas.product import ProductCreate, ProductRead, ProductUpdate


def _to_read(p: Product) -> ProductRead:
    return ProductRead(
        id=p.id, sku=p.sku, name=p.name, category=p.category,
        unit_weight_kg=float(p.unit_weight_kg),
        unit_volume_cbm=float(p.unit_volume_cbm),
        price=float(p.price),
        created_at=p.created_at,
    )


def list_products(db: Session, page: int = 1, page_size: int = 20,
                  category: str = None, sku: str = None):
    q = db.query(Product)
    if category:
        q = q.filter(Product.category.ilike(f"%{category}%"))
    if sku:
        q = q.filter(Product.sku.ilike(f"%{sku}%"))
    total = q.count()
    products = q.order_by(Product.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return make_page([_to_read(p) for p in products], total, page, page_size)


def create_product(db: Session, data: ProductCreate) -> ProductRead:
    existing = db.query(Product).filter(Product.sku == data.sku).first()
    if existing:
        raise HTTPException(status_code=409, detail={"code": "DUPLICATE_RESOURCE", "message": f"SKU '{data.sku}' already exists.", "details": {}})
    product = Product(
        sku=data.sku, name=data.name, category=data.category,
        unit_weight_kg=data.unit_weight_kg,
        unit_volume_cbm=data.unit_volume_cbm,
        price=data.price,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return _to_read(product)


def get_product(db: Session, product_id: int) -> ProductRead:
    p = db.query(Product).filter(Product.id == product_id).first()
    if p is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Product not found.", "details": {}})
    return _to_read(p)


def update_product(db: Session, product_id: int, data: ProductUpdate) -> ProductRead:
    p = db.query(Product).filter(Product.id == product_id).first()
    if p is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Product not found.", "details": {}})
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return _to_read(p)


def delete_product(db: Session, product_id: int) -> None:
    from backend.app.models.warehouse import Inventory
    from backend.app.models.order import OrderItem
    from backend.app.models.batch import PickRouteStep

    p = db.query(Product).filter(Product.id == product_id).first()
    if p is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Product not found.", "details": {}})

    inv_count = db.query(Inventory).filter(Inventory.product_id == product_id).count()
    if inv_count > 0:
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Cannot delete product ID {product_id}: referenced by {inv_count} inventory records.", "details": {}}
        )

    order_item_count = db.query(OrderItem).filter(OrderItem.product_id == product_id).count()
    if order_item_count > 0:
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Cannot delete product ID {product_id}: referenced by {order_item_count} order line items.", "details": {}}
        )

    step_count = db.query(PickRouteStep).filter(PickRouteStep.product_id == product_id).count()
    if step_count > 0:
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Cannot delete product ID {product_id}: referenced by {step_count} pick route steps.", "details": {}}
        )

    db.delete(p)
    db.commit()


def import_products(db: Session, file_content: str) -> dict:
    """Import CSV file containing products and upsert by SKU."""
    import csv
    import io

    created_count = 0
    updated_count = 0
    errors = []

    reader = csv.DictReader(io.StringIO(file_content))
    for row_num, row in enumerate(reader, start=2):
        sku = (row.get("sku") or "").strip()
        name = (row.get("name") or "").strip()
        category = (row.get("category") or "").strip()
        weight_str = (row.get("unit_weight_kg") or "").strip()
        vol_str = (row.get("unit_volume_cbm") or "").strip()
        price_str = (row.get("price") or "").strip()

        if not sku or not name:
            errors.append({"row": row_num, "message": "Missing required fields (sku or name)."})
            continue

        try:
            unit_weight_kg = float(weight_str) if weight_str else 1.0
            unit_volume_cbm = float(vol_str) if vol_str else 0.001
            price = float(price_str) if price_str else 10.0
        except ValueError:
            errors.append({"row": row_num, "message": "Invalid numeric format for weight, volume, or price."})
            continue

        existing = db.query(Product).filter(Product.sku == sku).first()
        if existing:
            existing.name = name
            existing.category = category or existing.category
            existing.unit_weight_kg = unit_weight_kg
            existing.unit_volume_cbm = unit_volume_cbm
            existing.price = price
            updated_count += 1
        else:
            p = Product(
                sku=sku,
                name=name,
                category=category or "General",
                unit_weight_kg=unit_weight_kg,
                unit_volume_cbm=unit_volume_cbm,
                price=price
            )
            db.add(p)
            created_count += 1

        db.commit()

    return {"created": created_count, "updated": updated_count, "errors": errors}


