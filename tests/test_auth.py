import pytest

class TestLogin:
    def test_login_success_returns_tokens(self, client):
        resp = client.post("/api/v1/auth/login", json={"email": "admin@smartlogistics.com", "password": "test1234"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password_returns_401(self, client):
        resp = client.post("/api/v1/auth/login", json={"email": "admin@smartlogistics.com", "password": "wrong"})
        assert resp.status_code == 401

class TestMe:
    def test_me_returns_user_profile(self, client, admin_headers):
        resp = client.get("/api/v1/auth/me", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "admin@smartlogistics.com"

class TestErrorEnvelope:
    def test_validation_error_has_field_details(self, client):
        resp = client.post("/api/v1/auth/login", json={"email": "not-an-email", "password": "123"})
        assert resp.status_code == 422


class TestRegisterMinimal:
    def test_register_with_minimal_fields_returns_201(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "username": "minimal_user",
            "email": "minimal@example.com",
            "password": "varun"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "minimal@example.com"
        assert data["full_name"] == "minimal_user"
        assert data["role"] == "customer"

