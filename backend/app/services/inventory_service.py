"""Inventory service."""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.app.models.warehouse import Inventory, StorageLocation, WarehouseNode, Product
from backend.app.schemas.common import make_page
from backend.app.schemas.inventory import InventoryCreate, InventoryRead, InventoryUpdate


def _to_read(inv: Inventory) -> InventoryRead:
    return InventoryRead(
        id=inv.id,
        warehouse_id=inv.warehouse_id,
        product_id=inv.product_id,
        location_id=inv.location_id,
        quantity=inv.quantity,
        reorder_threshold=inv.reorder_threshold,
        updated_at=inv.updated_at,
    )


def list_inventory(db: Session, page: int = 1, page_size: int = 20,
                   warehouse_id: int = None, product_id: int = None):
    q = db.query(Inventory)
    if warehouse_id:
        q = q.filter(Inventory.warehouse_id == warehouse_id)
    if product_id:
        q = q.filter(Inventory.product_id == product_id)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return make_page([_to_read(i) for i in items], total, page, page_size)


def get_inventory(db: Session, inventory_id: int) -> InventoryRead:
    inv = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if inv is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Inventory record not found.", "details": {}})
    return _to_read(inv)


def upsert_inventory(db: Session, data: InventoryCreate) -> InventoryRead:
    # 1. Validate location belongs to warehouse
    loc = db.query(StorageLocation).join(WarehouseNode).filter(
        StorageLocation.id == data.location_id,
        WarehouseNode.warehouse_id == data.warehouse_id
    ).first()
    if not loc:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_ARGUMENT", "message": f"Storage location ID {data.location_id} does not belong to warehouse ID {data.warehouse_id}.", "details": {}}
        )

    # 2. Validate product exists
    prod = db.query(Product).filter(Product.id == data.product_id).first()
    if not prod:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Product ID {data.product_id} not found.", "details": {}}
        )

    # 3. Find existing or create
    inv = db.query(Inventory).filter(
        Inventory.warehouse_id == data.warehouse_id,
        Inventory.location_id == data.location_id,
        Inventory.product_id == data.product_id
    ).first()

    if inv:
        inv.quantity = data.quantity
        inv.reorder_threshold = data.reorder_threshold
    else:
        inv = Inventory(
            warehouse_id=data.warehouse_id,
            location_id=data.location_id,
            product_id=data.product_id,
            quantity=data.quantity,
            reorder_threshold=data.reorder_threshold
        )
        db.add(inv)

    db.commit()
    db.refresh(inv)
    return _to_read(inv)


def update_inventory(db: Session, inventory_id: int, data: InventoryUpdate) -> InventoryRead:
    inv = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if inv is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Inventory record not found.", "details": {}})
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(inv, field, value)
    db.commit()
    db.refresh(inv)
    return _to_read(inv)


def delete_inventory(db: Session, inventory_id: int) -> None:
    inv = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if inv is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Inventory record not found.", "details": {}})
    try:
        db.delete(inv)
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Cannot delete inventory record: {str(err)}", "details": {}}
        )


def import_inventory(db: Session, file_content: str) -> dict:
    """Import CSV file containing inventory records and upsert by (warehouse, location, product).
    Supports warehouse_code='*' to apply to all warehouses containing location_code.
    """
    import csv
    import io

    created_count = 0
    updated_count = 0
    errors = []
    per_warehouse_counts = {}

    reader = csv.DictReader(io.StringIO(file_content))
    for row_num, row in enumerate(reader, start=2):
        wh_code = (row.get("warehouse_code") or "").strip()
        loc_code = (row.get("location_code") or "").strip()
        sku = (row.get("sku") or "").strip()
        qty_str = (row.get("quantity") or "").strip()
        thresh_str = (row.get("reorder_threshold") or "").strip()

        if not wh_code or not loc_code or not sku:
            errors.append({"row": row_num, "message": "Missing required fields (warehouse_code, location_code, or sku)."})
            continue

        try:
            quantity = int(qty_str) if qty_str else 0
            reorder_threshold = int(thresh_str) if thresh_str else 10
        except ValueError:
            errors.append({"row": row_num, "message": "Invalid integer format for quantity or reorder_threshold."})
            continue

        prod = db.query(Product).filter(Product.sku == sku).first()
        if not prod:
            errors.append({"row": row_num, "message": f"Product SKU '{sku}' not found."})
            continue

        if wh_code == "*":
            from backend.app.models.warehouse import Warehouse
            matching_pairs = db.query(StorageLocation, Warehouse).join(
                WarehouseNode, StorageLocation.node_id == WarehouseNode.id
            ).join(
                Warehouse, WarehouseNode.warehouse_id == Warehouse.id
            ).filter(
                StorageLocation.location_code == loc_code
            ).all()

            if not matching_pairs:
                errors.append({"row": row_num, "message": f"No warehouses found with location_code '{loc_code}'."})
                continue

            for loc, wh in matching_pairs:
                existing = db.query(Inventory).filter(
                    Inventory.warehouse_id == wh.id,
                    Inventory.location_id == loc.id,
                    Inventory.product_id == prod.id
                ).first()

                if existing:
                    existing.quantity = quantity
                    existing.reorder_threshold = reorder_threshold
                    updated_count += 1
                else:
                    inv = Inventory(
                        warehouse_id=wh.id,
                        location_id=loc.id,
                        product_id=prod.id,
                        quantity=quantity,
                        reorder_threshold=reorder_threshold
                    )
                    db.add(inv)
                    created_count += 1

                per_warehouse_counts[wh.code] = per_warehouse_counts.get(wh.code, 0) + 1

            db.commit()
        else:
            from backend.app.models.warehouse import Warehouse
            wh = db.query(Warehouse).filter(Warehouse.code == wh_code).first()
            if not wh:
                errors.append({"row": row_num, "message": f"Warehouse code '{wh_code}' not found."})
                continue

            loc = db.query(StorageLocation).join(WarehouseNode).filter(
                WarehouseNode.warehouse_id == wh.id,
                StorageLocation.location_code == loc_code
            ).first()
            if not loc:
                errors.append({"row": row_num, "message": f"Storage location code '{loc_code}' not found in warehouse '{wh_code}'."})
                continue

            existing = db.query(Inventory).filter(
                Inventory.warehouse_id == wh.id,
                Inventory.location_id == loc.id,
                Inventory.product_id == prod.id
            ).first()

            if existing:
                existing.quantity = quantity
                existing.reorder_threshold = reorder_threshold
                updated_count += 1
            else:
                inv = Inventory(
                    warehouse_id=wh.id,
                    location_id=loc.id,
                    product_id=prod.id,
                    quantity=quantity,
                    reorder_threshold=reorder_threshold
                )
                db.add(inv)
                created_count += 1

            per_warehouse_counts[wh.code] = per_warehouse_counts.get(wh.code, 0) + 1
            db.commit()

    return {
        "created": created_count,
        "updated": updated_count,
        "per_warehouse_counts": per_warehouse_counts,
        "errors": errors
    }

