"""
Fraud Detection Engine
Contains rule-based scoring logic to evaluate transaction risk.
Risk Score Range: 0 to 100
- 0 to 39: Low Risk
- 40 to 69: Medium Risk
- 70 to 100: High Risk
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any


def calculate_risk_score(
    amount: float,
    timestamp: datetime,
    recent_transactions: Optional[List[datetime]] = None
) -> Dict[str, Any]:
    """
    Evaluates a transaction against defined fraud detection rules.

    Rules:
    1. Amount > 50,000: +40 points
    2. Time between 12:00 AM and 5:00 AM: +30 points
    3. More than 3 transactions by the same user within 10 minutes: +30 points

    Args:
        amount: Transaction monetary amount.
        timestamp: Datetime of the current transaction.
        recent_transactions: List of datetimes of previous transactions by the same user.

    Returns:
        dict containing:
            - risk_score: Integer (0-100)
            - risk_level: "Low", "Medium", or "High"
            - triggered_rules: List of human-readable rule descriptions with scores
    """
    score = 0
    triggered_rules = []

    # Rule 1: High Transaction Amount
    # Legitimate daily transactions are usually lower; massive sudden sums carry higher risk.
    if amount > 50000:
        score += 40
        triggered_rules.append("High transaction amount (> ₹50,000) [+40 pts]")

    # Rule 2: Night-time Transaction (12:00 AM to 5:00 AM)
    # Fraudulent automated withdrawals or compromised credentials frequently happen overnight.
    if 0 <= timestamp.hour < 5:
        score += 30
        triggered_rules.append("Night-time transaction (12:00 AM - 5:00 AM) [+30 pts]")

    # Rule 3: Velocity Check (>3 transactions in a 10-minute window)
    # Fraudsters or bots frequently attempt credential testing or rapid fund siphon.
    if recent_transactions:
        ten_minutes_before = timestamp - timedelta(minutes=10)
        # Count transactions occurring within the 10-minute window preceding the transaction
        count_in_window = sum(
            1 for t in recent_transactions
            if ten_minutes_before <= t <= timestamp
        )
        if count_in_window > 3:
            score += 30
            triggered_rules.append("Rapid velocity: >3 transactions within 10 minutes [+30 pts]")

    # Ensure score stays within bounded range [0, 100]
    score = min(max(score, 0), 100)

    # Classify Risk Level
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
