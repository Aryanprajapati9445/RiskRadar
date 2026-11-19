"""
Database Models for Fraud Detection Dashboard
Uses Flask-SQLAlchemy with SQLite
"""

import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    """System User supporting Role-Based Access Control (Admin & Analyst)."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="analyst")  # 'admin' or 'analyst'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Transaction(db.Model):
    """Monitored Financial Transaction with Risk Scoring and Status tracking."""
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    city = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(30), nullable=False)  # UPI, Card, NetBanking, ATM
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Fraud Engine evaluation fields
    risk_score = db.Column(db.Integer, nullable=False, default=0)
    risk_level = db.Column(db.String(20), nullable=False, default="Low")  # Low, Medium, High
    triggered_rules = db.Column(db.Text, default="[]")  # JSON string of triggered rules

    # Status: Safe, Flagged, Confirmed Fraud, Blocked
    status = db.Column(db.String(30), nullable=False, default="Safe")
    notes = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to investigation history
    cases = db.relationship("InvestigationCase", backref="transaction", lazy=True, cascade="all, delete-orphan")

    def get_rules_list(self):
        """Parse JSON-encoded triggered rules string."""
        try:
            return json.loads(self.triggered_rules) if self.triggered_rules else []
        except Exception:
            return []

    def set_rules_list(self, rules_list):
        """Store list of triggered rules as JSON string."""
        self.triggered_rules = json.dumps(rules_list)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": self.amount,
            "city": self.city,
            "type": self.type,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else None,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "triggered_rules": self.get_rules_list(),
            "status": self.status,
            "notes": self.notes or "",
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None
        }


class InvestigationCase(db.Model):
    """Investigation audit trail when an analyst/admin marks or updates a case."""
    __tablename__ = "investigation_cases"

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transactions.id"), nullable=False, index=True)
    action = db.Column(db.String(30), nullable=False)  # "Confirmed Fraud", "Safe", "Blocked"
    notes = db.Column(db.Text, nullable=True)
    analyst_username = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "action": self.action,
            "notes": self.notes,
            "analyst_username": self.analyst_username,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        }
