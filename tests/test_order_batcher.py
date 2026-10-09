"""
Unit tests for Phase 3.2 Order Batching Engine.
Tests eligibility evaluation, FIFO baseline, Priority-Heuristic optimization, capacity limits, stock checks, and performance comparison.
"""
from datetime import datetime, timezone, timedelta
import pytest

from backend.app.services.order_batcher import (
    OrderBatchingEngine, OrderDTO, OrderItemDTO, BatchingConstraints, BatchingConfig
)


@pytest.fixture
def sample_orders() -> list[OrderDTO]:
    now = datetime.now(timezone.utc)
    return [
        OrderDTO(
            id=1, order_number="ORD-001", warehouse_id=1, priority=1, status="pending",
            created_at=now - timedelta(minutes=30), promised_at=now + timedelta(hours=2),
            items=[OrderItemDTO(product_id=101, quantity=2, unit_weight_kg=2.0, unit_volume_cbm=0.01)]
        ),
        OrderDTO(
            id=2, order_number="ORD-002", warehouse_id=1, priority=3, status="pending", # URGENT
            created_at=now - timedelta(minutes=20), promised_at=now + timedelta(hours=1),
            items=[OrderItemDTO(product_id=102, quantity=1, unit_weight_kg=5.0, unit_volume_cbm=0.02)]
        ),
        OrderDTO(
            id=3, order_number="ORD-003", warehouse_id=1, priority=2, status="pending", # HIGH
            created_at=now - timedelta(minutes=10), promised_at=now + timedelta(hours=1, minutes=30),
            items=[OrderItemDTO(product_id=101, quantity=1, unit_weight_kg=2.0, unit_volume_cbm=0.01)]
        ),
        OrderDTO(
            id=4, order_number="ORD-004", warehouse_id=1, priority=1, status="pending",
            created_at=now - timedelta(minutes=5), promised_at=now + timedelta(hours=3),
            items=[OrderItemDTO(product_id=103, quantity=3, unit_weight_kg=3.0, unit_volume_cbm=0.01)]
        ),
        OrderDTO(
            id=5, order_number="ORD-005", warehouse_id=1, priority=1, status="delivered", # INVALID STATUS
            created_at=now, promised_at=now + timedelta(hours=4),
            items=[OrderItemDTO(product_id=101, quantity=1, unit_weight_kg=1.0, unit_volume_cbm=0.01)]
        ),
    ]


def test_empty_orders():
    res = OrderBatchingEngine.batch_fifo([])
    assert res.total_orders_evaluated == 0
    assert res.eligible_orders_count == 0
    assert res.batch_count == 0
    assert res.generated_batches == []


def test_single_order(sample_orders):
    single = [sample_orders[0]]
    res = OrderBatchingEngine.batch_fifo(single)
    assert res.eligible_orders_count == 1
    assert res.batch_count == 1
    assert res.generated_batches[0].order_ids == [1]


def test_eligibility_filtering(sample_orders):
    # Order 5 has status 'delivered' -> should be ineligible
    stock_map = {101: 10, 102: 10, 103: 10}
    eligible, unassigned = OrderBatchingEngine.evaluate_eligibility(sample_orders, inventory_stock_map=stock_map, target_warehouse_id=1)
    
    assert len(eligible) == 4
    assert 5 in unassigned
    assert "status 'delivered'" in unassigned[5].lower()


def test_insufficient_inventory(sample_orders):
    # Product 102 has only 0 in stock -> Order 2 (requires 1) must be rejected
    stock_map = {101: 10, 102: 0, 103: 10}
    eligible, unassigned = OrderBatchingEngine.evaluate_eligibility(sample_orders, inventory_stock_map=stock_map, target_warehouse_id=1)
    
    assert len(eligible) == 3
    assert 2 in unassigned
    assert "insufficient stock" in unassigned[2].lower()


def test_fifo_baseline_order(sample_orders):
    stock_map = {101: 10, 102: 10, 103: 10}
    res = OrderBatchingEngine.batch_fifo(sample_orders, inventory_stock_map=stock_map, target_warehouse_id=1)
    
    assert res.strategy_name == "fifo_baseline"
    assert res.eligible_orders_count == 4
    assert res.batch_count == 1
    # FIFO order sequence: 1, 2, 3, 4
    assert res.generated_batches[0].order_ids == [1, 2, 3, 4]


def test_priority_heuristic_order(sample_orders):
    stock_map = {101: 10, 102: 10, 103: 10}
    res = OrderBatchingEngine.batch_priority_heuristic(sample_orders, inventory_stock_map=stock_map, target_warehouse_id=1)
    
    assert res.strategy_name == "priority_heuristic"
    assert res.eligible_orders_count == 4
    # Priority order sequence: Priority 3 (Ord 2), Priority 2 (Ord 3), Priority 1 (Ord 1, Ord 4)
    assert res.generated_batches[0].order_ids == [2, 3, 1, 4]


def test_capacity_limit_split():
    now = datetime.now(timezone.utc)
    # Create 6 orders with max_orders_per_batch = 3
    orders = [
        OrderDTO(
            id=i, order_number=f"ORD-00{i}", warehouse_id=1, priority=1, status="pending",
            created_at=now, promised_at=now,
            items=[OrderItemDTO(product_id=100, quantity=1, unit_weight_kg=2.0, unit_volume_cbm=0.01)]
        ) for i in range(1, 7)
    ]
    constraints = BatchingConstraints(max_orders_per_batch=3)
    res = OrderBatchingEngine.batch_priority_heuristic(orders, constraints=constraints)
    
    assert res.batch_count == 2
    assert len(res.generated_batches[0].order_ids) == 3
    assert len(res.generated_batches[1].order_ids) == 3


def test_weight_capacity_overflow():
    now = datetime.now(timezone.utc)
    # Create single heavy order (30kg) with max_weight = 25kg
    heavy = [
        OrderDTO(
            id=1, order_number="ORD-HEAVY", warehouse_id=1, priority=1, status="pending",
            created_at=now, promised_at=now,
            items=[OrderItemDTO(product_id=100, quantity=1, unit_weight_kg=30.0, unit_volume_cbm=0.01)]
        )
    ]
    constraints = BatchingConstraints(max_weight_kg=25.0)
    res = OrderBatchingEngine.batch_priority_heuristic(heavy, constraints=constraints)
    
    assert res.eligible_orders_count == 0
    assert 1 in res.unassigned_orders
    assert "exceeds batch max weight" in res.unassigned_reasons[1]


def test_determinism(sample_orders):
    stock_map = {101: 10, 102: 10, 103: 10}
    res1 = OrderBatchingEngine.batch_priority_heuristic(sample_orders, inventory_stock_map=stock_map)
    res2 = OrderBatchingEngine.batch_priority_heuristic(sample_orders, inventory_stock_map=stock_map)
    
    assert res1.generated_batches == res2.generated_batches
    assert res1.objective_value == res2.objective_value
