"""
Application Routes and REST API Endpoints
Serves both HTML UI pages and JSON REST APIs.
"""

from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, jsonify, Response
)
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import func, or_

from app.models import db, User, Transaction, InvestigationCase
from app.fraud_engine import calculate_risk_score
from app.metrics import FLAGGED_TRANSACTIONS_GAUGE, TOTAL_TRANSACTIONS_GAUGE

main_bp = Blueprint("main", __name__)


# -------------------------------------------------------------
# Authentication & Role Decorators
# -------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("main.login_view"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session or session["user"].get("role") != "admin":
            flash("Admin access required for this action.", "danger")
            return redirect(url_for("main.dashboard_view"))
        return f(*args, **kwargs)
    return decorated_function


# -------------------------------------------------------------
# Web UI Pages
# -------------------------------------------------------------
@main_bp.route("/")
def index():
    if "user" in session:
        return redirect(url_for("main.dashboard_view"))
    return redirect(url_for("main.login_view"))


@main_bp.route("/login", methods=["GET", "POST"])
def login_view():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user"] = {
                "id": user.id,
                "username": user.username,
                "role": user.role
            }
            flash(f"Welcome back, {user.username}! Signed in as {user.role.title()}.", "success")
            return redirect(url_for("main.dashboard_view"))

        flash("Invalid username or password. Use admin/admin123 or analyst/analyst123.", "danger")

    return render_template("login.html")


@main_bp.route("/logout")
def logout_view():
    session.pop("user", None)
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("main.login_view"))


@main_bp.route("/dashboard")
@login_required
def dashboard_view():
    return render_template("dashboard.html", user=session.get("user"))


@main_bp.route("/transactions")
@login_required
def transactions_view():
    page = request.args.get("page", 1, type=int)
    risk_level = request.args.get("risk_level", "").strip()
    status = request.args.get("status", "").strip()
    search = request.args.get("search", "").strip()

    query = Transaction.query

    if search:
        query = query.filter(
            or_(
                Transaction.user_id.ilike(f"%{search}%"),
                Transaction.city.ilike(f"%{search}%"),
                Transaction.type.ilike(f"%{search}%")
            )
        )

    if risk_level and risk_level != "All":
        query = query.filter(Transaction.risk_level == risk_level)

    if status and status != "All":
        query = query.filter(Transaction.status == status)

    pagination = query.order_by(Transaction.timestamp.desc()).paginate(
        page=page, per_page=15, error_out=False
    )

    return render_template(
        "transactions.html",
        transactions=pagination.items,
        pagination=pagination,
        search=search,
        risk_level=risk_level,
        status=status,
        user=session.get("user")
    )


@main_bp.route("/investigate/<int:id>")
@login_required
def investigate_view(id):
    transaction = Transaction.query.get_or_404(id)
    cases = InvestigationCase.query.filter_by(transaction_id=id).order_by(InvestigationCase.created_at.desc()).all()
    return render_template("investigate.html", txn=transaction, cases=cases, user=session.get("user"))


@main_bp.route("/add-transaction", methods=["GET", "POST"])
@login_required
def add_transaction_view():
    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip().upper()
        amount_raw = request.form.get("amount", "0")
        city = request.form.get("city", "Delhi")
        txn_type = request.form.get("type", "UPI")

        try:
            amount = float(amount_raw)
            if amount <= 0:
                raise ValueError()
        except ValueError:
            flash("Please enter a valid positive transaction amount.", "danger")
            return redirect(url_for("main.add_transaction_view"))

        txn_time = datetime.utcnow()

        # Check recent transactions of this user in past 15 minutes for velocity check
        ten_mins_ago = txn_time - timedelta(minutes=15)
        recent_txns = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.timestamp >= ten_mins_ago,
            Transaction.timestamp <= txn_time
        ).all()
        recent_timestamps = [t.timestamp for t in recent_txns]

        scoring = calculate_risk_score(amount, txn_time, recent_timestamps)
        status = "Flagged" if scoring["risk_score"] >= 40 else "Safe"

        new_txn = Transaction(
            user_id=user_id,
            amount=amount,
            city=city,
            type=txn_type,
            timestamp=txn_time,
            risk_score=scoring["risk_score"],
            risk_level=scoring["risk_level"],
            status=status
        )
        new_txn.set_rules_list(scoring["triggered_rules"])

        db.session.add(new_txn)
        db.session.commit()

        flash(
            f"Transaction #{new_txn.id} created! "
            f"Risk Score: {new_txn.risk_score} ({new_txn.risk_level}) - Status: {status}",
            "warning" if status == "Flagged" else "success"
        )
        return redirect(url_for("main.investigate_view", id=new_txn.id))

    return render_template("add_transaction.html", user=session.get("user"))


# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------
@main_bp.route("/api/transactions", methods=["GET"])
def api_get_transactions():
    """Retrieve transactions with search, filtering, and pagination."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    risk_level = request.args.get("risk_level", "").strip()
    status = request.args.get("status", "").strip()
    search = request.args.get("search", "").strip()

    query = Transaction.query

    if search:
        query = query.filter(
            or_(
                Transaction.user_id.ilike(f"%{search}%"),
                Transaction.city.ilike(f"%{search}%"),
                Transaction.type.ilike(f"%{search}%")
            )
        )

    if risk_level:
        query = query.filter(Transaction.risk_level == risk_level)

    if status:
        query = query.filter(Transaction.status == status)

    pagination = query.order_by(Transaction.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        "success": True,
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
        "pages": pagination.pages,
        "transactions": [t.to_dict() for t in pagination.items]
    }), 200


@main_bp.route("/api/transactions/<int:id>", methods=["GET"])
def api_get_transaction(id):
    """Retrieve a single transaction by ID."""
    txn = db.session.get(Transaction, id)
    if not txn:
        return jsonify({"success": False, "error": "Transaction not found"}), 404
    return jsonify({"success": True, "transaction": txn.to_dict()}), 200


@main_bp.route("/api/transactions", methods=["POST"])
def api_create_transaction():
    """
    Create a new transaction and immediately evaluate with Fraud Engine.
    Expected JSON body:
      - user_id (string, required)
      - amount (number, required)
      - city (string, optional - defaults to 'Delhi')
      - type (string, optional - defaults to 'UPI')
      - timestamp (string ISO, optional - defaults to now)
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Invalid JSON body"}), 400

    user_id = data.get("user_id", "").strip().upper()
    amount = data.get("amount")
    city = data.get("city", "Delhi")
    txn_type = data.get("type", "UPI")
    custom_ts = data.get("timestamp")

    if not user_id or amount is None:
        return jsonify({"success": False, "error": "user_id and amount are required"}), 400

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError()
    except ValueError:
        return jsonify({"success": False, "error": "amount must be a positive number"}), 400

    if custom_ts:
        try:
            txn_time = datetime.fromisoformat(custom_ts.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            txn_time = datetime.utcnow()
    else:
        txn_time = datetime.utcnow()

    # Query user transactions in the preceding 15 minutes
    ten_mins_ago = txn_time - timedelta(minutes=15)
    recent_txns = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.timestamp >= ten_mins_ago,
        Transaction.timestamp <= txn_time
    ).all()
    recent_timestamps = [t.timestamp for t in recent_txns]

    # Evaluate risk score
    scoring = calculate_risk_score(amount, txn_time, recent_timestamps)
    status = "Flagged" if scoring["risk_score"] >= 40 else "Safe"

    txn = Transaction(
        user_id=user_id,
        amount=amount,
        city=city,
        type=txn_type,
        timestamp=txn_time,
        risk_score=scoring["risk_score"],
        risk_level=scoring["risk_level"],
        status=status
    )
    txn.set_rules_list(scoring["triggered_rules"])

    db.session.add(txn)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Transaction scored and saved successfully",
        "transaction": txn.to_dict()
    }), 201


@main_bp.route("/api/transactions/<int:id>/status", methods=["PUT"])
def api_update_transaction_status(id):
    """
    Update status of a transaction (Investigation Action).
    Supported statuses: "Confirmed Fraud", "Safe", "Blocked"
    Saves an InvestigationCase record.
    """
    txn = db.session.get(Transaction, id)
    if not txn:
        return jsonify({"success": False, "error": "Transaction not found"}), 404

    data = request.get_json() or {}
    new_status = data.get("status")
    notes = data.get("notes", "").strip()

    valid_statuses = ["Confirmed Fraud", "Safe", "Blocked", "Flagged"]
    if new_status not in valid_statuses:
        return jsonify({
            "success": False,
            "error": f"Invalid status. Choose from: {', '.join(valid_statuses)}"
        }), 400

    analyst_name = session.get("user", {}).get("username", "api_client")

    txn.status = new_status
    txn.notes = notes
    txn.updated_at = datetime.utcnow()

    # Create Case record
    case_record = InvestigationCase(
        transaction_id=txn.id,
        action=new_status,
        notes=notes,
        analyst_username=analyst_name
    )

    db.session.add(case_record)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Transaction #{id} updated to {new_status}",
        "transaction": txn.to_dict(),
        "case": case_record.to_dict()
    }), 200


@main_bp.route("/api/stats", methods=["GET"])
def api_get_stats():
    """Returns aggregated stats for dashboard KPI cards and Chart.js."""
    total = Transaction.query.count()
    flagged = Transaction.query.filter(
        or_(
            Transaction.status == "Flagged",
            Transaction.status == "Confirmed Fraud",
            Transaction.status == "Blocked",
            Transaction.risk_score >= 40
        )
    ).count()

    high_risk = Transaction.query.filter(Transaction.risk_level == "High").count()
    medium_risk = Transaction.query.filter(Transaction.risk_level == "Medium").count()
    low_risk = Transaction.query.filter(Transaction.risk_level == "Low").count()

    fraud_percentage = round((flagged / total * 100), 2) if total > 0 else 0.0

    # Alerts over time (last 7 days grouped by date)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    daily_alerts = db.session.query(
        func.date(Transaction.timestamp).label("date"),
        func.count(Transaction.id).label("count")
    ).filter(
        Transaction.timestamp >= seven_days_ago,
        Transaction.risk_score >= 40
    ).group_by(func.date(Transaction.timestamp)).order_by("date").all()

    timeline_labels = [row.date for row in daily_alerts]
    timeline_values = [row.count for row in daily_alerts]

    # If timeline is empty (e.g. initial launch), provide fallback empty sequence
    if not timeline_labels:
        for i in range(6, -1, -1):
            d_str = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            timeline_labels.append(d_str)
            timeline_values.append(0)

    return jsonify({
        "success": True,
        "cards": {
            "total_transactions": total,
            "flagged_transactions": flagged,
            "high_risk_count": high_risk,
            "fraud_percentage": fraud_percentage
        },
        "risk_distribution": {
            "labels": ["Low Risk", "Medium Risk", "High Risk"],
            "counts": [low_risk, medium_risk, high_risk]
        },
        "alerts_timeline": {
            "labels": timeline_labels,
            "data": timeline_values
        }
    }), 200


# -------------------------------------------------------------
# DevOps Health & Prometheus Metrics Endpoints
# -------------------------------------------------------------
@main_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Docker, Kubernetes, and uptime probes."""
    try:
        # Check SQLite DB connection
        db.session.execute(func.now()).scalar()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    total_count = Transaction.query.count() if db_status == "connected" else 0

    return jsonify({
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "service": "fraud-detection-dashboard",
        "database": db_status,
        "total_transactions": total_count,
        "timestamp": datetime.utcnow().isoformat()
    }), 200 if db_status == "connected" else 503


@main_bp.route("/metrics", methods=["GET"])
def metrics():
    """Prometheus metrics endpoint scraped by Prometheus daemon."""
    # Update current database gauges
    try:
        total = Transaction.query.count()
        flagged = Transaction.query.filter(
            or_(
                Transaction.status == "Flagged",
                Transaction.status == "Confirmed Fraud",
                Transaction.status == "Blocked",
                Transaction.risk_score >= 40
            )
        ).count()
        TOTAL_TRANSACTIONS_GAUGE.set(total)
        FLAGGED_TRANSACTIONS_GAUGE.set(flagged)
    except Exception:
        pass

    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
