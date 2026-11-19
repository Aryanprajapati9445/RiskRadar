"""
Prometheus Metrics Configuration
Defines application metrics exported at /metrics endpoint
"""

import time
from flask import request
from prometheus_client import Counter, Histogram, Gauge


# 1. Total HTTP Requests Counter (labels: method, endpoint, status)
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP Requests handled by the application",
    ["method", "endpoint", "status"]
)

# 2. HTTP Request Latency Histogram
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP Request Latency in seconds",
    ["endpoint"]
)

# 3. Fraud Flagged Transactions Gauge
FLAGGED_TRANSACTIONS_GAUGE = Gauge(
    "fraud_flagged_transactions_total",
    "Current total number of flagged suspicious transactions"
)

# 4. Total Transactions Gauge
TOTAL_TRANSACTIONS_GAUGE = Gauge(
    "fraud_transactions_total",
    "Current total number of transactions in the database"
)


def setup_metrics(app):
    """Hooks request timing & status code tracking into Flask application lifecycle."""

    @app.before_request
    def before_request_hook():
        request._start_time = time.time()

    @app.after_request
    def after_request_hook(response):
        if hasattr(request, "_start_time"):
            duration = time.time() - request._start_time
            endpoint = request.endpoint or request.path
            REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration)
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                status=response.status_code
            ).step_index = 0 if hasattr(REQUEST_COUNT, "step_index") else None
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                status=str(response.status_code)
            ).inc()

        return response
