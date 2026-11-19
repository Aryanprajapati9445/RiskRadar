/**
 * Dashboard Analytics and Chart.js Controller
 * Loads metrics from /api/stats and renders interactive charts.
 */

document.addEventListener("DOMContentLoaded", function () {
    fetchDashboardStats();
});

let riskChartInstance = null;
let timelineChartInstance = null;

async function fetchDashboardStats() {
    try {
        const response = await fetch("/api/stats");
        if (!response.ok) {
            throw new Error("Failed to load statistics from API");
        }
        const data = await response.json();
        if (data.success) {
            updateKpiCards(data.cards);
            renderRiskDistributionChart(data.risk_distribution);
            renderAlertsTimelineChart(data.alerts_timeline);
        }
    } catch (error) {
        console.error("Error fetching dashboard statistics:", error);
    }
}

function updateKpiCards(cards) {
    const totalEl = document.getElementById("kpi-total");
    const flaggedEl = document.getElementById("kpi-flagged");
    const highRiskEl = document.getElementById("kpi-high-risk");
    const rateEl = document.getElementById("kpi-rate");

    if (totalEl) totalEl.textContent = cards.total_transactions.toLocaleString();
    if (flaggedEl) flaggedEl.textContent = cards.flagged_transactions.toLocaleString();
    if (highRiskEl) highRiskEl.textContent = cards.high_risk_count.toLocaleString();
    if (rateEl) rateEl.textContent = cards.fraud_percentage.toFixed(2) + "%";
}

function renderRiskDistributionChart(dist) {
    const ctx = document.getElementById("riskDistributionChart");
    if (!ctx) return;

    if (riskChartInstance) {
        riskChartInstance.destroy();
    }

    riskChartInstance = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: dist.labels,
            datasets: [{
                data: dist.counts,
                backgroundColor: [
                    "#22c55e", // Low (Green)
                    "#f59e0b", // Medium (Amber)
                    "#ef4444"  // High (Red)
                ],
                borderWidth: 2,
                borderColor: "#ffffff"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        boxWidth: 12,
                        padding: 15,
                        font: { size: 12 }
                    }
                }
            },
            cutout: "65%"
        }
    });
}

function renderAlertsTimelineChart(timeline) {
    const ctx = document.getElementById("alertsTimelineChart");
    if (!ctx) return;

    if (timelineChartInstance) {
        timelineChartInstance.destroy();
    }

    timelineChartInstance = new Chart(ctx, {
        type: "line",
        data: {
            labels: timeline.labels,
            datasets: [{
                label: "Suspicious Flagged Transactions",
                data: timeline.data,
                borderColor: "#ef4444",
                backgroundColor: "rgba(239, 68, 68, 0.12)",
                fill: true,
                tension: 0.35,
                borderWidth: 2.5,
                pointBackgroundColor: "#ef4444",
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    },
                    grid: {
                        color: "#f1f5f9"
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}
