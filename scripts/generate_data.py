"""
Data Generation Script for Fraud Detection Dashboard
Generates 1,000 realistic transactions with ~5% intentional fraud patterns.
Also seeds default Admin and Analyst user accounts.
"""

import sys
import os
import random
from datetime import datetime, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import db, User, Transaction  # noqa: E402
from app.fraud_engine import calculate_risk_score  # noqa: E402


CITIES = ["Delhi", "Mumbai", "Bangalore", "Chennai", "Kolkata"]
PAYMENT_TYPES = ["UPI", "Card", "NetBanking", "ATM"]


def seed_default_users():
    """Seeds default admin and analyst users if they do not exist."""
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(username="admin", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)
        print("  [+] Seeded admin user (admin / admin123)")

    analyst = User.query.filter_by(username="analyst").first()
    if not analyst:
        analyst = User(username="analyst", role="analyst")
        analyst.set_password("analyst123")
        db.session.add(analyst)
        print("  [+] Seeded analyst user (analyst / analyst123)")

    db.session.commit()


def generate_fake_transactions(total_count: int = 1000):
    """
    Generates realistic transactions over the past 7 days,
    including ~5% suspicious patterns (high amount, night hours, high velocity).
    """
    now = datetime.utcnow()
    user_pool = [f"USR{i:04d}" for i in range(1001, 1151)]  # 150 unique users

    # Track user transaction timestamps to properly evaluate Rule 3 (velocity)
    user_history = {uid: [] for uid in user_pool}
    created_transactions = []

    print(f"Generating {total_count} transactions...")

    # We will generate ~950 regular transactions and ~50 suspicious pattern transactions
    suspicious_count = int(total_count * 0.05)
    normal_count = total_count - suspicious_count

    # 1. Normal Transactions
    for _ in range(normal_count):
        user_id = random.choice(user_pool)
        # Normal amounts: 100 to 45,000 (below 50,000 threshold)
        amount = round(random.uniform(100, 45000), 2)
        city = random.choice(CITIES)
        p_type = random.choice(PAYMENT_TYPES)

        # Normal hours: daytime (07:00 to 23:00)
        days_ago = random.uniform(0.1, 7.0)
        base_date = now - timedelta(days=days_ago)
        random_hour = random.randint(7, 23)
        random_minute = random.randint(0, 59)
        random_second = random.randint(0, 59)
        txn_time = base_date.replace(hour=random_hour, minute=random_minute, second=random_second)

        created_transactions.append({
            "user_id": user_id,
            "amount": amount,
            "city": city,
            "type": p_type,
            "timestamp": txn_time
        })

    # 2. Suspicious Patterns (~50 transactions)
    # Pattern A: High amount (> 50,000)
    for _ in range(20):
        user_id = random.choice(user_pool)
        amount = round(random.uniform(50500, 99999), 2)
        city = random.choice(CITIES)
        p_type = random.choice(PAYMENT_TYPES)
        days_ago = random.uniform(0.1, 6.5)
        txn_time = now - timedelta(days=days_ago)

        created_transactions.append({
            "user_id": user_id,
            "amount": amount,
            "city": city,
            "type": p_type,
            "timestamp": txn_time
        })

    # Pattern B: Night-time transactions (12:00 AM - 4:59 AM)
    for _ in range(18):
        user_id = random.choice(user_pool)
        amount = round(random.uniform(2000, 65000), 2)
        city = random.choice(CITIES)
        p_type = random.choice(PAYMENT_TYPES)
        days_ago = random.uniform(0.1, 6.5)
        night_date = now - timedelta(days=days_ago)
        night_hour = random.randint(0, 4)
        night_min = random.randint(0, 59)
        txn_time = night_date.replace(hour=night_hour, minute=night_min, second=random.randint(0, 59))

        created_transactions.append({
            "user_id": user_id,
            "amount": amount,
            "city": city,
            "type": p_type,
            "timestamp": txn_time
        })

    # Pattern C: Rapid velocity (>3 transactions by same user within 10 minutes)
    for _ in range(3):  # 3 clusters of 4 rapid transactions = 12 transactions
        burst_user = random.choice(user_pool)
        burst_base = now - timedelta(days=random.uniform(0.5, 5.0))
        burst_city = random.choice(CITIES)
        burst_type = "UPI"

        for offset_min in [1, 3, 5, 8]:
            txn_time = burst_base + timedelta(minutes=offset_min)
            amount = round(random.uniform(500, 55000), 2)
            created_transactions.append({
                "user_id": burst_user,
                "amount": amount,
                "city": burst_city,
                "type": burst_type,
                "timestamp": txn_time
            })

    # Sort all transactions chronologically so velocity checks evaluate accurately
    created_transactions.sort(key=lambda x: x["timestamp"])

    # Score each transaction and build Transaction model instances
    db_objects = []
    flagged_count = 0

    for item in created_transactions:
        u_id = item["user_id"]
        t_time = item["timestamp"]

        # Run through fraud engine with user's past transactions
        recent_history = user_history.get(u_id, [])
        scoring = calculate_risk_score(item["amount"], t_time, recent_history)

        # Update user history
        user_history[u_id].append(t_time)

        # Determine status
        is_flagged = scoring["risk_score"] >= 40
        status = "Flagged" if is_flagged else "Safe"
        if is_flagged:
            flagged_count += 1

        txn = Transaction(
            user_id=u_id,
            amount=item["amount"],
            city=item["city"],
            type=item["type"],
            timestamp=t_time,
            risk_score=scoring["risk_score"],
            risk_level=scoring["risk_level"],
            status=status
        )
        txn.set_rules_list(scoring["triggered_rules"])
        db_objects.append(txn)

    # Bulk save to DB in batches
    db.session.bulk_save_objects(db_objects)
    db.session.commit()

    print(f"  [+] Inserted {len(db_objects)} transactions into database.")
    print(f"  [+] Suspicious / Flagged transactions: {flagged_count} (~{flagged_count/len(db_objects)*100:.1f}%)")


def run_seeding(app):
    """Entrypoint to seed database inside Flask application context."""
    with app.app_context():
        db.create_all()
        seed_default_users()

        count = Transaction.query.count()
        if count == 0:
            print("Database has 0 transactions. Running initial data generator...")
            generate_fake_transactions(1000)
        else:
            print(f"Database already contains {count} transactions. Skipping transaction seeding.")


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    run_seeding(app)
