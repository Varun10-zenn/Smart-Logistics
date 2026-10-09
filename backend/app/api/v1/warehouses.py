"""Warehouses router."""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import require_role
from backend.app.schemas.common import Page
from backend.app.schemas.warehouse import (
    WarehouseCreate, WarehouseRead, WarehouseUpdate, WarehouseGraphRead,
    NodeRead, EdgeRead, StorageLocationRead, WarehouseValidationRead,
    WarehouseZoneCreate, WarehouseZoneRead, WarehouseZoneUpdate,
    WarehouseNodeCreate, WarehouseNodeUpdate,
    WarehouseEdgeCreate, WarehouseEdgeUpdate,
    StorageLocationCreate, StorageLocationUpdate,
    LayoutGenerateRequest
)
from backend.app.services import warehouse_service

router = APIRouter(prefix="/warehouses", tags=["Warehouses"])

_READ_ROLES = ("admin", "warehouse_operator", "fleet_manager")
_ADMIN_ROLES = ("admin",)


# --- Warehouses Master ---
@router.get("", response_model=Page[WarehouseRead])
def list_warehouses(
    page: int = 1, page_size: int = 20, status: str = None,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return warehouse_service.list_warehouses(db, page, page_size, status)


@router.post("", response_model=WarehouseRead, status_code=201)
def create_warehouse(
    data: WarehouseCreate,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    return warehouse_service.create_warehouse(db, data)


@router.post("/import", summary="Import Zepto store locations from CSV (admin only)")
async def import_warehouses_csv(
    file: UploadFile = File(...),
    generate_layout: bool = Form(True),
    aisles: int = Form(4),
    shelves_per_aisle: int = Form(5),
    aisle_spacing_m: float = Form(3.0),
    shelf_spacing_m: float = Form(2.0),
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    content = (await file.read()).decode("utf-8")
    return warehouse_service.import_stores_csv(
        db,
        csv_content=content,
        generate_layout=generate_layout,
        aisles=aisles,
        shelves_per_aisle=shelves_per_aisle,
        aisle_spacing_m=aisle_spacing_m,
        shelf_spacing_m=shelf_spacing_m,
    )


@router.get("/{warehouse_id}", response_model=WarehouseRead)
def get_warehouse(
    warehouse_id: int,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return warehouse_service.get_warehouse(db, warehouse_id)


@router.patch("/{warehouse_id}", response_model=WarehouseRead)
def update_warehouse(
    warehouse_id: int, data: WarehouseUpdate,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    return warehouse_service.update_warehouse(db, warehouse_id, data)


@router.delete("/{warehouse_id}", status_code=204)
def delete_warehouse(
    warehouse_id: int,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    warehouse_service.delete_warehouse(db, warehouse_id)


# --- Layout Validation & Generation ---
@router.get("/{warehouse_id}/validate", response_model=WarehouseValidationRead)
def validate_warehouse_layout(
    warehouse_id: int,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return warehouse_service.validate_warehouse_layout(db, warehouse_id)


@router.post("/{warehouse_id}/layout/generate", response_model=WarehouseGraphRead, status_code=201)
def generate_warehouse_layout(
    warehouse_id: int,
    data: LayoutGenerateRequest,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    return warehouse_service.generate_warehouse_layout(
        db=db,
        warehouse_id=warehouse_id,
        aisles=data.aisles,
        shelves_per_aisle=data.shelves_per_aisle,
        aisle_spacing_m=data.aisle_spacing_m,
        shelf_spacing_m=data.shelf_spacing_m,
        replace_existing=data.replace_existing
    )


# --- Zones ---
@router.get("/{warehouse_id}/zones", response_model=List[WarehouseZoneRead])
def list_zones(
    warehouse_id: int,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return warehouse_service.list_zones(db, warehouse_id)


@router.post("/{warehouse_id}/zones", response_model=WarehouseZoneRead, status_code=201)
def create_zone(
    warehouse_id: int, data: WarehouseZoneCreate,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    return warehouse_service.create_zone(db, warehouse_id, data)


@router.patch("/{warehouse_id}/zones/{zone_id}", response_model=WarehouseZoneRead)
def update_zone(
    warehouse_id: int, zone_id: int, data: WarehouseZoneUpdate,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    return warehouse_service.update_zone(db, warehouse_id, zone_id, data)


@router.delete("/{warehouse_id}/zones/{zone_id}", status_code=204)
def delete_zone(
    warehouse_id: int, zone_id: int,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    warehouse_service.delete_zone(db, warehouse_id, zone_id)


# --- Nodes ---
@router.get("/{warehouse_id}/nodes", response_model=List[NodeRead])
def list_nodes(
    warehouse_id: int,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return warehouse_service.list_nodes(db, warehouse_id)


@router.post("/{warehouse_id}/nodes", response_model=NodeRead, status_code=201)
def create_node(
    warehouse_id: int, data: WarehouseNodeCreate,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    return warehouse_service.create_node(db, warehouse_id, data)


@router.patch("/{warehouse_id}/nodes/{node_id}", response_model=NodeRead)
def update_node(
    warehouse_id: int, node_id: int, data: WarehouseNodeUpdate,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    return warehouse_service.update_node(db, warehouse_id, node_id, data)


@router.delete("/{warehouse_id}/nodes/{node_id}", status_code=204)
def delete_node(
    warehouse_id: int, node_id: int,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    warehouse_service.delete_node(db, warehouse_id, node_id)


# --- Edges ---
@router.get("/{warehouse_id}/edges", response_model=List[EdgeRead])
def list_edges(
    warehouse_id: int,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return warehouse_service.list_edges(db, warehouse_id)


@router.post("/{warehouse_id}/edges", response_model=EdgeRead, status_code=201)
def create_edge(
    warehouse_id: int, data: WarehouseEdgeCreate,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    return warehouse_service.create_edge(db, warehouse_id, data)


@router.patch("/{warehouse_id}/edges/{edge_id}", response_model=EdgeRead)
def update_edge(
    warehouse_id: int, edge_id: int, data: WarehouseEdgeUpdate,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    return warehouse_service.update_edge(db, warehouse_id, edge_id, data)


@router.delete("/{warehouse_id}/edges/{edge_id}", status_code=204)
def delete_edge(
    warehouse_id: int, edge_id: int,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    warehouse_service.delete_edge(db, warehouse_id, edge_id)


# --- Storage Locations ---
@router.get("/{warehouse_id}/locations", response_model=List[StorageLocationRead])
def list_locations(
    warehouse_id: int,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return warehouse_service.list_locations(db, warehouse_id)


@router.post("/{warehouse_id}/locations", response_model=StorageLocationRead, status_code=201)
def create_location(
    warehouse_id: int, data: StorageLocationCreate,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    return warehouse_service.create_location(db, warehouse_id, data)


@router.patch("/{warehouse_id}/locations/{location_id}", response_model=StorageLocationRead)
def update_location(
    warehouse_id: int, location_id: int, data: StorageLocationUpdate,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    return warehouse_service.update_location(db, warehouse_id, location_id, data)


@router.delete("/{warehouse_id}/locations/{location_id}", status_code=204)
def delete_location(
    warehouse_id: int, location_id: int,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    warehouse_service.delete_location(db, warehouse_id, location_id)


# --- Graph & Optimization ---
@router.get("/{warehouse_id}/graph", response_model=WarehouseGraphRead)
def get_warehouse_graph(
    warehouse_id: int,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    try:
        return warehouse_service.get_warehouse_graph(db, warehouse_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": str(exc), "details": {}},
        )


@router.post("/{warehouse_id}/path")
def calculate_shortest_path(
    warehouse_id: int,
    payload: Dict[str, Any],
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    from backend.app.services.warehouse_agent_tools import dispatch_warehouse_tool
    tool_payload = dict(payload)
    tool_payload["warehouse_id"] = warehouse_id
    res = dispatch_warehouse_tool(db, current_user.role.code, "calculate_shortest_path", tool_payload)
    if not res.get("success"):
        code = "NOT_FOUND" if "not found" in res.get("error", "").lower() else "INVALID_ARGUMENT"
        status_code = 404 if code == "NOT_FOUND" else 400
        raise HTTPException(
            status_code=status_code,
            detail={"code": code, "message": res.get("error"), "details": {}},
        )
    return res


@router.post("/{warehouse_id}/batch")
def generate_order_batches(
    warehouse_id: int,
    payload: Dict[str, Any],
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    from backend.app.services.warehouse_agent_tools import dispatch_warehouse_tool
    tool_payload = dict(payload)
    tool_payload["warehouse_id"] = warehouse_id
    res = dispatch_warehouse_tool(db, current_user.role.code, "generate_order_batches", tool_payload)
    if not res.get("success"):
        code = "NOT_FOUND" if "not found" in res.get("error", "").lower() else "INVALID_ARGUMENT"
        status_code = 404 if code == "NOT_FOUND" else 400
        raise HTTPException(
            status_code=status_code,
            detail={"code": code, "message": res.get("error"), "details": {}},
        )
    return res


@router.post("/{warehouse_id}/pick-route")
def generate_pick_route(
    warehouse_id: int,
    payload: Dict[str, Any],
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    from backend.app.services.warehouse_agent_tools import dispatch_warehouse_tool
    tool_payload = dict(payload)
    tool_payload["warehouse_id"] = warehouse_id
    res = dispatch_warehouse_tool(db, current_user.role.code, "generate_pick_route", tool_payload)
    if not res.get("success"):
        code = "NOT_FOUND" if "not found" in res.get("error", "").lower() else "INVALID_ARGUMENT"
        status_code = 404 if code == "NOT_FOUND" else 400
        raise HTTPException(
            status_code=status_code,
            detail={"code": code, "message": res.get("error"), "details": {}},
        )
    return res


@router.post("/{warehouse_id}/optimize")
def optimize_warehouse(
    warehouse_id: int,
    payload: Dict[str, Any] = None,
    current_user=Depends(require_role("admin", "warehouse_operator")),
    db: Session = Depends(get_db),
):
    from backend.app.services.warehouse_optimization_service import WarehouseOptimizationService
    from backend.app.services.order_batcher import BatchingConstraints
    from backend.app.services.warehouse_agent_tools import dispatch_warehouse_tool

    if payload and "operation" in payload:
        op = payload["operation"]
        tool_payload = dict(payload.get("payload", {}))
        tool_payload["warehouse_id"] = warehouse_id
        res = dispatch_warehouse_tool(db, current_user.role.code, op, tool_payload)
        return {"success": True, "operation": op, "data": res}

    constraints = None
    if payload:
        if "constraints" in payload:
            c_dict = payload["constraints"]
            constraints = BatchingConstraints(
                max_orders_per_batch=c_dict.get("max_orders_per_batch", 5),
                max_weight_kg=c_dict.get("max_weight_kg", 25.0),
                max_volume_cbm=c_dict.get("max_volume_cbm", 0.12),
            )
        elif any(k in payload for k in ("max_orders_per_batch", "max_weight_kg", "max_volume_cbm")):
            constraints = BatchingConstraints(
                max_orders_per_batch=payload.get("max_orders_per_batch", 5),
                max_weight_kg=payload.get("max_weight_kg", 25.0),
                max_volume_cbm=payload.get("max_volume_cbm", 0.12),
            )

    use_2opt = payload.get("use_2opt_routing", True) if payload else True

    res = WarehouseOptimizationService.optimize_warehouse(
        db=db,
        warehouse_id=warehouse_id,
        batch_constraints=constraints,
        use_2opt_routing=use_2opt
    )

    if not res.success:
        code = "VALIDATION_ERROR" if "validation" in (res.failure_reason or "").lower() or "depot" in (res.failure_reason or "").lower() else "INVALID_ARGUMENT"
        status_code = 422 if code == "VALIDATION_ERROR" else 400
        raise HTTPException(
            status_code=status_code,
            detail={"code": code, "message": res.failure_reason, "details": {}},
        )
    return res.model_dump()


@router.get("/{warehouse_id}/metrics")
def get_warehouse_metrics(
    warehouse_id: int,
    current_user=Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    from backend.app.services.warehouse_agent_tools import dispatch_warehouse_tool
    res = dispatch_warehouse_tool(db, current_user.role.code, "calculate_warehouse_metrics", {"warehouse_id": warehouse_id})
    if not res.get("success"):
        code = "NOT_FOUND" if "not found" in res.get("error", "").lower() else "INVALID_ARGUMENT"
        status_code = 404 if code == "NOT_FOUND" else 400
        raise HTTPException(
            status_code=status_code,
            detail={"code": code, "message": res.get("error"), "details": {}},
        )
    return res


@router.post("/{warehouse_id}/fleet/generate", summary="Generate store riders and EV/ICE vehicles")
def generate_fleet(
    warehouse_id: int,
    payload: Dict[str, Any],
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    from backend.app.services import delivery_service
    riders_count = int(payload.get("riders", 2))
    ev_count = int(payload.get("ev_count", 1))
    return delivery_service.generate_store_fleet(db, warehouse_id, riders_count, ev_count)


@router.post("/{warehouse_id}/charging/generate", summary="Generate store depot chargers")
def generate_depot_chargers(
    warehouse_id: int,
    payload: Dict[str, Any] = None,
    current_user=Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    from backend.app.services import charging_service
    connectors_count = int((payload or {}).get("connectors", 2))
    max_power_kw = float((payload or {}).get("max_power_kw", 50.0))
    price_per_kwh = float((payload or {}).get("price_per_kwh", 0.0))
    st = charging_service.generate_depot_chargers(
        db, warehouse_id, connectors_count=connectors_count,
        max_power_kw=max_power_kw, price_per_kwh=price_per_kwh
    )
    return {
        "message": f"Depot chargers generated for warehouse #{warehouse_id}",
        "station_id": st.id,
        "station_code": st.station_code,
        "total_connectors": st.total_connectors
    }

