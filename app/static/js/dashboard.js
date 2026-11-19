/**
 * FraudGuard CyberOps - Analytics & Chart Controller
 * Renders high-tech linear gradients and dark theme charts.
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

    if (totalEl) totalEl.textContent = Number(cards.total_transactions).toLocaleString();
    if (flaggedEl) flaggedEl.textContent = Number(cards.flagged_transactions).toLocaleString();
    if (highRiskEl) highRiskEl.textContent = Number(cards.high_risk_count).toLocaleString();
    if (rateEl) rateEl.textContent = Number(cards.fraud_percentage).toFixed(2) + "%";
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
                    "#10b981", // Low Risk (Cyber Emerald)
                    "#f59e0b", // Medium Risk (Cyber Amber)
                    "#f43f5e"  // High Risk (Crimson Danger)
                ],
                borderWidth: 2,
                borderColor: "#0f172a",
                hoverOffset: 6
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
                        padding: 16,
                        color: "#94a3b8",
                        font: { 
                            size: 12, 
                            family: "'Inter', sans-serif",
                            weight: 500
                        }
                    }
                },
                tooltip: {
                    backgroundColor: "rgba(15, 23, 42, 0.95)",
                    borderColor: "rgba(255, 255, 255, 0.1)",
                    borderWidth: 1,
                    titleColor: "#ffffff",
                    bodyColor: "#94a3b8",
                    padding: 12,
                    boxPadding: 6,
                    cornerRadius: 8
                }
            },
            cutout: "70%"
        }
    });
}

function renderAlertsTimelineChart(timeline) {
    const ctx = document.getElementById("alertsTimelineChart");
    if (!ctx) return;

    if (timelineChartInstance) {
        timelineChartInstance.destroy();
    }

    const canvas = ctx.getContext("2d");
    const gradient = canvas.createLinearGradient(0, 0, 0, 280);
    gradient.addColorStop(0, "rgba(244, 63, 94, 0.35)");
    gradient.addColorStop(1, "rgba(244, 63, 94, 0.0)");

    timelineChartInstance = new Chart(ctx, {
        type: "line",
        data: {
            labels: timeline.labels,
            datasets: [{
                label: "Suspicious Flagged Transactions",
                data: timeline.data,
                borderColor: "#f43f5e",
                backgroundColor: gradient,
                fill: true,
                tension: 0.38,
                borderWidth: 3,
                pointBackgroundColor: "#f43f5e",
                pointBorderColor: "#0f172a",
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                        color: "#64748b",
                        font: { family: "'JetBrains Mono', monospace", size: 11 }
                    },
                    grid: {
                        color: "rgba(255, 255, 255, 0.04)"
                    }
                },
                x: {
                    ticks: {
                        color: "#64748b",
                        font: { family: "'JetBrains Mono', monospace", size: 11 }
                    },
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: "rgba(15, 23, 42, 0.95)",
                    borderColor: "rgba(244, 63, 94, 0.4)",
                    borderWidth: 1,
                    titleColor: "#ffffff",
                    bodyColor: "#f43f5e",
                    padding: 12,
                    boxPadding: 6,
                    cornerRadius: 8
                }
            }
        }
    });
}
