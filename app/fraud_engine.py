"""
Fraud Detection Engine
Comprehensive rule-based scoring logic to evaluate transaction risk.
Risk Score Range: 0 to 100
- 0 to 39: Low Risk (Safe)
- 40 to 69: Medium Risk (Flagged)
- 70 to 100: High Risk (Critical Flagged)
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple


def _normalize_history(recent_transactions: Optional[List[Any]]) -> List[Dict[str, Any]]:
    """Normalize input transaction history into a standard list of dictionaries."""
    history = []
    if not recent_transactions:
        return history

    for item in recent_transactions:
        if isinstance(item, datetime):
            history.append({
                "timestamp": item,
                "city": None,
                "amount": None,
                "type": None
            })
        elif isinstance(item, dict):
            history.append(item)
        elif hasattr(item, "timestamp"):
            history.append({
                "timestamp": getattr(item, "timestamp"),
                "city": getattr(item, "city", None),
                "amount": getattr(item, "amount", None),
                "type": getattr(item, "type", None)
            })
    return history


def _check_amount_rules(amount: float) -> Tuple[int, List[str]]:
    """Evaluate monetary threshold rules."""
    pts = 0
    rules = []
    if amount > 50000:
        pts += 40
        rules.append("High transaction amount (> ₹50,000) [+40 pts]")
    if amount > 85000:
        pts += 20
        rules.append("Critical payload threshold (> ₹85,000) [+20 pts]")
    return pts, rules


def _check_temporal_rules(timestamp: datetime) -> Tuple[int, List[str]]:
    """Evaluate off-hour / night-time transaction window."""
    if 0 <= timestamp.hour < 5:
        return 30, ["Night-time transaction (12:00 AM - 5:00 AM) [+30 pts]"]
    return 0, []


def _check_velocity_and_probe_rules(
    amount: float,
    timestamp: datetime,
    history: List[Dict[str, Any]]
) -> Tuple[int, List[str]]:
    """Evaluate rapid velocity spikes and repetitive exact amount card probes."""
    pts = 0
    rules = []
    if not history:
        return pts, rules

    # Velocity check: >3 transactions in last 10 minutes
    ten_mins_ago = timestamp - timedelta(minutes=10)
    count_in_10m = sum(1 for h in history if ten_mins_ago <= h["timestamp"] <= timestamp)
    if count_in_10m > 3:
        pts += 30
        rules.append("Rapid velocity: >3 transactions within 10 minutes [+30 pts]")

    # Repetitive card testing probe check: same amount >= 2 times in 15 minutes
    fifteen_mins_ago = timestamp - timedelta(minutes=15)
    identical_count = sum(
        1 for h in history
        if fifteen_mins_ago <= h["timestamp"] <= timestamp
        and h.get("amount") is not None
        and abs(h["amount"] - amount) < 0.01
    )
    if identical_count >= 2:
        pts += 20
        rules.append("Repetitive identical amount probe (Card testing pattern) [+20 pts]")

    return pts, rules


def _check_travel_and_channel_rules(
    city: Optional[str],
    payment_type: Optional[str],
    amount: float,
    timestamp: datetime,
    history: List[Dict[str, Any]]
) -> Tuple[int, List[str]]:
    """Evaluate geographic impossibility and high-risk physical cash channels."""
    pts = 0
    rules = []

    # Impossible Travel Anomaly (different city within 1 hour)
    if city and history:
        one_hour_ago = timestamp - timedelta(hours=1)
        prev_city_txns = [
            h for h in history
            if one_hour_ago <= h["timestamp"] <= timestamp
            and h.get("city") and h.get("city") != city
        ]
        if prev_city_txns:
            prev_city = prev_city_txns[-1]["city"]
            pts += 35
            rules.append(f"Impossible travel anomaly: Active in {city} within 1 hr of {prev_city} [+35 pts]")

    # High-Risk Physical ATM Cash Siphon (> ₹25,000 at ATM)
    if payment_type and payment_type.upper() == "ATM" and amount > 25000:
        pts += 25
        rules.append("High-value physical ATM withdrawal (> ₹25,000) [+25 pts]")

    return pts, rules


def calculate_risk_score(
    amount: float,
    timestamp: datetime,
    recent_transactions: Optional[List[Any]] = None,
    city: Optional[str] = None,
    payment_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates a transaction against comprehensive fraud detection rules.

    Rules:
    1. High Monetary Value (> ₹50,000): +40 points
    2. Critical Luxury Threshold (> ₹85,000): +20 points
    3. Night-Time Execution Window (12:00 AM - 5:00 AM): +30 points
    4. Velocity Spike (> 3 transactions in 10 minutes): +30 points
    5. Impossible Travel Anomaly (different city within 1 hr): +35 points
    6. High-Risk Physical ATM Cash Withdrawal (> ₹25,000): +25 points
    7. Repetitive Identical Amount Probe (Card testing pattern): +20 points
    """
    score = 0
    triggered_rules = []

    history = _normalize_history(recent_transactions)

    # 1. Monetary rules
    p1, r1 = _check_amount_rules(amount)
    score += p1
    triggered_rules.extend(r1)

    # 2. Temporal rules
    p2, r2 = _check_temporal_rules(timestamp)
    score += p2
    triggered_rules.extend(r2)

    # 3. Velocity and card testing rules
    p3, r3 = _check_velocity_and_probe_rules(amount, timestamp, history)
    score += p3
    triggered_rules.extend(r3)

    # 4. Impossible travel and channel rules
    p4, r4 = _check_travel_and_channel_rules(city, payment_type, amount, timestamp, history)
    score += p4
    triggered_rules.extend(r4)

    # Bound score in [0, 100]
    score = min(max(score, 0), 100)

    # Risk level classification
    if score >= 70:
        risk_level = "High"
    elif score >= 40:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return {
        "risk_score": score,
        "risk_level": risk_level,
        "triggered_rules": triggered_rules
    }
