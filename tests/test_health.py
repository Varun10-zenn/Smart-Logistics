import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "health" in data


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "environment" in data
    assert "database" in data
    assert "database_type" in data["database"]


def test_health_db_endpoint():
    response = client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["connected", "connected_fallback", "disconnected"]
    assert "database_type" in data
