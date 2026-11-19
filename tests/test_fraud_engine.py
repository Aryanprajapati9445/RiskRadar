"""
Unit Tests for Rule-Based Fraud Detection Engine (fraud_engine.py)
"""

from datetime import datetime, timedelta
from app.fraud_engine import calculate_risk_score


def test_normal_transaction_low_risk():
    """A regular daytime transaction below 50k should have score 0 and Low risk."""
    timestamp = datetime(2026, 11, 19, 14, 30, 0)  # 2:30 PM
    res = calculate_risk_score(amount=5000.0, timestamp=timestamp)

    assert res["risk_score"] == 0
    assert res["risk_level"] == "Low"
    assert len(res["triggered_rules"]) == 0


def test_amount_above_50k_triggers_rule():
    """An amount > 50,000 adds 40 points and classifies as Medium risk."""
    timestamp = datetime(2026, 11, 19, 14, 30, 0)
    res = calculate_risk_score(amount=50001.0, timestamp=timestamp)

    assert res["risk_score"] == 40
    assert res["risk_level"] == "Medium"
    assert len(res["triggered_rules"]) == 1
    assert "High transaction amount" in res["triggered_rules"][0]


def test_amount_boundary_50k_not_triggered():
    """Boundary test: exactly 50,000 does NOT exceed threshold."""
    timestamp = datetime(2026, 11, 19, 15, 0, 0)
    res = calculate_risk_score(amount=50000.0, timestamp=timestamp)

    assert res["risk_score"] == 0
    assert res["risk_level"] == "Low"
    assert len(res["triggered_rules"]) == 0


def test_night_time_transaction():
    """Transaction between 12 AM and 5 AM adds 30 points."""
    # 2:15 AM
    timestamp = datetime(2026, 11, 19, 2, 15, 0)
    res = calculate_risk_score(amount=2500.0, timestamp=timestamp)

    assert res["risk_score"] == 30
    assert res["risk_level"] == "Low"
    assert len(res["triggered_rules"]) == 1
    assert "Night-time" in res["triggered_rules"][0]


def test_night_time_boundary_5am_not_triggered():
    """Boundary test: 5:00 AM is outside 12:00 AM - 4:59:59 AM."""
    timestamp = datetime(2026, 11, 19, 5, 0, 0)
    res = calculate_risk_score(amount=2500.0, timestamp=timestamp)

    assert res["risk_score"] == 0
    assert len(res["triggered_rules"]) == 0


def test_high_amount_and_night_time_high_risk():
    """Amount > 50k (+40) + Night time (+30) = 70 points (High risk)."""
    timestamp = datetime(2026, 11, 19, 1, 30, 0)  # 1:30 AM
    res = calculate_risk_score(amount=75000.0, timestamp=timestamp)

    assert res["risk_score"] == 70
    assert res["risk_level"] == "High"
    assert len(res["triggered_rules"]) == 2


def test_velocity_exceeds_threshold():
    """More than 3 transactions in 10 minutes adds 30 points."""
    curr = datetime(2026, 11, 19, 16, 10, 0)
    recent = [
        curr - timedelta(minutes=2),
        curr - timedelta(minutes=4),
        curr - timedelta(minutes=7),
        curr - timedelta(minutes=9)
    ]  # 4 past transactions in 10 min window

    res = calculate_risk_score(amount=1000.0, timestamp=curr, recent_transactions=recent)

    assert res["risk_score"] == 30
    assert res["risk_level"] == "Low"
    assert len(res["triggered_rules"]) == 1
    assert "Rapid velocity" in res["triggered_rules"][0]


def test_velocity_exactly_3_transactions_not_triggered():
    """Boundary test: exactly 3 past transactions does NOT trigger (>3 required)."""
    curr = datetime(2026, 11, 19, 16, 10, 0)
    recent = [
        curr - timedelta(minutes=2),
        curr - timedelta(minutes=4),
        curr - timedelta(minutes=6)
    ]  # exactly 3

    res = calculate_risk_score(amount=1000.0, timestamp=curr, recent_transactions=recent)

    assert res["risk_score"] == 0
    assert len(res["triggered_rules"]) == 0


def test_all_rules_combined_max_score_100():
    """All 3 rules active: 40 + 30 + 30 = 100 points (High risk)."""
    curr = datetime(2026, 11, 19, 3, 10, 0)  # Night
    recent = [
        curr - timedelta(minutes=1),
        curr - timedelta(minutes=2),
        curr - timedelta(minutes=3),
        curr - timedelta(minutes=5)
    ]  # Velocity

    res = calculate_risk_score(amount=85000.0, timestamp=curr, recent_transactions=recent)

    assert res["risk_score"] == 100
    assert res["risk_level"] == "High"
    assert len(res["triggered_rules"]) == 3
