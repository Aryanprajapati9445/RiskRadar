"""
Integration and Functional Tests for Flask REST APIs and Web Routes
"""

import pytest
from app import create_app
from app.models import db, User, Transaction


@pytest.fixture
def app():
    """Create and configure a clean testing app instance with an in-memory SQLite database."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key"
    })

    with app.app_context():
        db.create_all()
        # Seed users
        admin = User(username="admin", role="admin")
        admin.set_password("admin123")
        analyst = User(username="analyst", role="analyst")
        analyst.set_password("analyst123")
        db.session.add_all([admin, analyst])

        # Seed sample transaction
        txn = Transaction(
            user_id="USR9999",
            amount=60000.0,
            city="Delhi",
            type="UPI",
            risk_score=40,
            risk_level="Medium",
            status="Flagged"
        )
        txn.set_rules_list(["High transaction amount (> ₹50,000) [+40 pts]"])
        db.session.add(txn)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_health_check_endpoint(client):
    """GET /health should return 200 with service and database status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "fraud-detection-dashboard"
    assert data["database"] == "connected"
    assert data["total_transactions"] >= 1


def test_prometheus_metrics_endpoint(client):
    """GET /metrics should return Prometheus formatted metrics."""
    response = client.get("/metrics")
    assert response.status_code == 200
    text = response.data.decode("utf-8")
    assert "http_requests_total" in text
    assert "fraud_flagged_transactions_total" in text


def test_get_transactions_api(client):
    """GET /api/transactions should return paginated transactions."""
    response = client.get("/api/transactions")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["total"] >= 1
    assert len(data["transactions"]) >= 1
    assert data["transactions"][0]["user_id"] == "USR9999"


def test_get_transactions_filter_risk_level(client):
    """GET /api/transactions?risk_level=Medium should filter properly."""
    response = client.get("/api/transactions?risk_level=Medium")
    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] >= 1

    # Filter with High should yield 0 since only Medium was seeded
    response_high = client.get("/api/transactions?risk_level=High")
    assert response_high.get_json()["total"] == 0


def test_get_transaction_by_id(client):
    """GET /api/transactions/<id> should return a specific transaction."""
    response = client.get("/api/transactions/1")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["transaction"]["id"] == 1
    assert data["transaction"]["amount"] == 60000.0


def test_get_transaction_by_id_not_found(client):
    """GET /api/transactions/99999 should return 404."""
    response = client.get("/api/transactions/99999")
    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False


def test_create_transaction_api_high_risk(client):
    """POST /api/transactions should score transaction immediately."""
    payload = {
        "user_id": "USR2026",
        "amount": 72000.0,
        "city": "Mumbai",
        "type": "Card",
        "timestamp": "2026-11-19T02:30:00"  # Night + High amount = 70 (High)
    }
    response = client.post("/api/transactions", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    txn = data["transaction"]
    assert txn["risk_score"] == 70
    assert txn["risk_level"] == "High"
    assert txn["status"] == "Flagged"
    assert len(txn["triggered_rules"]) == 2


def test_create_transaction_api_invalid_payload(client):
    """POST /api/transactions with missing amount should return 400."""
    response = client.post("/api/transactions", json={"user_id": "USR100"})
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False


def test_update_transaction_status_and_case_creation(client):
    """PUT /api/transactions/<id>/status should update status and log case."""
    payload = {
        "status": "Confirmed Fraud",
        "notes": "Customer confirmed unapproved card swipe"
    }
    response = client.put("/api/transactions/1/status", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["transaction"]["status"] == "Confirmed Fraud"
    assert data["case"]["action"] == "Confirmed Fraud"
    assert "Customer confirmed" in data["case"]["notes"]


def test_update_transaction_status_invalid_status(client):
    """PUT /api/transactions/<id>/status with invalid status should return 400."""
    response = client.put("/api/transactions/1/status", json={"status": "NonExistentStatus"})
    assert response.status_code == 400


def test_get_stats_api(client):
    """GET /api/stats should return summary cards and chart series."""
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "cards" in data
    assert "total_transactions" in data["cards"]
    assert "risk_distribution" in data
    assert "alerts_timeline" in data


def test_auth_login_and_logout_flow(client):
    """Test session-based login and logout."""
    # Invalid password
    bad_login = client.post("/login", data={"username": "admin", "password": "wrongpassword"}, follow_redirects=True)
    assert b"Invalid username or password" in bad_login.data

    # Valid analyst login
    good_login = client.post("/login", data={"username": "analyst", "password": "analyst123"}, follow_redirects=True)
    assert good_login.status_code == 200
    assert b"Signed in as Analyst" in good_login.data

    # Logout
    logout_res = client.get("/logout", follow_redirects=True)
    assert b"You have been signed out successfully" in logout_res.data
