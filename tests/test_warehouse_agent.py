"""
Tests for Phase 3.6 — Warehouse Optimization AI Agent.
"""

import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models.warehouse import Warehouse, WarehouseZone, WarehouseNode, WarehouseEdge
from backend.app.models.intelligence import AIRecommendation
from backend.app.services.warehouse_agent import (
    WarehouseOptimizationAgent,
    AgentOptimizationRequest,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    # Seed sample warehouse
    wh = Warehouse(name="Agent Test Warehouse", code="WH-AGT-01", latitude=10.0, longitude=20.0, address="123 Test St")
    db.add(wh)
    db.commit()
    db.refresh(wh)

    z = WarehouseZone(warehouse_id=wh.id, zone_code="ZA", name="Zone A", zone_type="storage")
    db.add(z)
    db.commit()
    db.refresh(z)

    n1 = WarehouseNode(warehouse_id=wh.id, zone_id=z.id, node_code="N1", x_coord=0.0, y_coord=0.0)
    n2 = WarehouseNode(warehouse_id=wh.id, zone_id=z.id, node_code="N2", x_coord=10.0, y_coord=0.0)
    db.add_all([n1, n2])
    db.commit()
    db.refresh(n1)
    db.refresh(n2)

    e = WarehouseEdge(warehouse_id=wh.id, from_node_id=n1.id, to_node_id=n2.id, distance_meters=10.0, is_bidirectional=True)
    db.add(e)
    db.commit()

    yield db
    db.close()


def test_valid_agent_request(db_session):
    agent = WarehouseOptimizationAgent()
    req = AgentOptimizationRequest(
        warehouse_id=1,
        operation="get_warehouse_graph",
        payload={"warehouse_id": 1},
        user_prompt="Provide warehouse graph structure",
    )
    res = agent.execute_request(db_session, req, user_role="warehouse_operator")
    assert res.success is True
    assert res.operation == "get_warehouse_graph"
    assert res.tool_result["total_nodes"] == 2
    assert res.fallback_used is True  # LLM client is None
    assert "deterministic algorithm rules" in res.explanation

    # Check audit log in DB
    audit = db_session.query(AIRecommendation).filter(AIRecommendation.recommendation_type == "get_warehouse_graph").first()
    assert audit is not None
    assert audit.agent_name == "WarehouseOptimizationAgent"


def test_unauthorized_request(db_session):
    agent = WarehouseOptimizationAgent()
    req = AgentOptimizationRequest(
        warehouse_id=1,
        operation="get_warehouse_graph",
        payload={"warehouse_id": 1},
    )
    res = agent.execute_request(db_session, req, user_role="driver")
    assert res.success is False
    assert "not authorized" in res.explanation
    assert res.confidence_score == 0.0


def test_invalid_tool_request(db_session):
    agent = WarehouseOptimizationAgent()
    req = AgentOptimizationRequest(
        warehouse_id=1,
        operation="arbitrary_hack_tool",
        payload={},
    )
    res = agent.execute_request(db_session, req, user_role="admin")
    assert res.success is False
    assert "Unknown tool" in res.explanation


def test_tool_failure_handling(db_session):
    agent = WarehouseOptimizationAgent()
    req = AgentOptimizationRequest(
        warehouse_id=9999,  # Non-existent warehouse
        operation="get_warehouse_graph",
        payload={"warehouse_id": 9999},
    )
    res = agent.execute_request(db_session, req, user_role="admin")
    assert res.success is False
    assert res.tool_result["success"] is False
    assert "Warehouse with ID 9999 not found" in res.explanation


def test_llm_integration_success(db_session):
    mock_llm = MagicMock()
    mock_llm.generate.return_value = {
        "explanation": "The warehouse contains 2 connected nodes forming a simple path.",
        "summary": {"nodes": 2},
    }
    agent = WarehouseOptimizationAgent(llm_client=mock_llm)
    req = AgentOptimizationRequest(
        warehouse_id=1,
        operation="get_warehouse_graph",
        payload={"warehouse_id": 1},
    )
    res = agent.execute_request(db_session, req, user_role="admin")
    assert res.success is True
    assert res.llm_used is True
    assert res.fallback_used is False
    assert "The warehouse contains 2 connected nodes" in res.explanation


def test_llm_failure_deterministic_fallback(db_session):
    mock_llm = MagicMock()
    mock_llm.generate.side_effect = Exception("API rate limit / network error")
    agent = WarehouseOptimizationAgent(llm_client=mock_llm)
    req = AgentOptimizationRequest(
        warehouse_id=1,
        operation="get_warehouse_graph",
        payload={"warehouse_id": 1},
    )
    res = agent.execute_request(db_session, req, user_role="admin")
    assert res.success is True
    assert res.llm_used is False
    assert res.fallback_used is True
    assert "Retrieved warehouse graph" in res.explanation


def test_malformed_llm_output_rejection(db_session):
    mock_llm = MagicMock()
    mock_llm.generate.return_value = "This is not a structured dict!"
    agent = WarehouseOptimizationAgent(llm_client=mock_llm)
    req = AgentOptimizationRequest(
        warehouse_id=1,
        operation="get_warehouse_graph",
        payload={"warehouse_id": 1},
    )
    res = agent.execute_request(db_session, req, user_role="admin")
    assert res.success is True
    assert res.llm_used is False
    assert res.fallback_used is True


def test_hallucinated_entity_rejection(db_session):
    mock_llm = MagicMock()
    mock_llm.generate.return_value = {
        "explanation": "We recommend moving to hallucinated_node_99 which is optimal.",
        "summary": {},
    }
    agent = WarehouseOptimizationAgent(llm_client=mock_llm)
    req = AgentOptimizationRequest(
        warehouse_id=1,
        operation="get_warehouse_graph",
        payload={"warehouse_id": 1},
    )
    res = agent.execute_request(db_session, req, user_role="admin")
    assert res.success is True
    assert res.llm_used is False
    assert res.fallback_used is True
