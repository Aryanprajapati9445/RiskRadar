"""
Flask Application Factory for Fraud Detection Dashboard
"""

import os
from flask import Flask
from app.models import db
from app.metrics import setup_metrics


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    # Base configuration
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    db_path = os.path.join(base_dir, "fraud_dashboard.db")

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "fraud-detection-dev-key-2026"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", f"sqlite:///{db_path}"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config:
        app.config.update(test_config)

    # Initialize database
    db.init_app(app)

    # Setup Prometheus metrics hooks
    setup_metrics(app)

    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # Ensure tables exist and auto-seed initial data if empty (unless in test mode)
    if not app.config.get("TESTING"):
        with app.app_context():
            db.create_all()
            try:
                from scripts.generate_data import seed_default_users, generate_fake_transactions
                from app.models import Transaction
                seed_default_users()
                if Transaction.query.count() == 0:
                    print("Auto-seeding initial 1,000 transactions...")
                    generate_fake_transactions(1000)
            except Exception as e:
                print(f"Notice during seeding: {e}")

    return app
