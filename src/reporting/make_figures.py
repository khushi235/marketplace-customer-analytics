"""Charts used in the README and in the monthly review deck.

Matplotlib rather than a BI tool here, because these need to regenerate automatically with
the rest of the report. Anything interactive lives in Power BI.
"""

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.analysis import cohorts, kpis, rfm  # noqa: E402
from src.db import load_orders  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

FIG_DIR = Path(__file__).resolve().parents[2] / "reports" / "figures"
INK = "#1f2933"
ACCENT = "#2563eb"
PALETTE = ["#2563eb", "#7c3aed", "#0891b2", "#059669", "#d97706", "#dc2626", "#64748b", "#be185d"]


def _style(ax, title: str, xlabel: str = "", ylabel: str = ""):
    ax.set_title(title, fontsize=13, fontweight="bold", color=INK, pad=12)
    ax.set_xlabel(xlabel, fontsize=10, color=INK)
    ax.set_ylabel(ylabel, fontsize=10, color=INK)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25, linewidth=0.7)
    ax.tick_params(colors=INK, labelsize=9)


def _save(fig, name: str):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIG_DIR / name, dpi=150, facecolor="white")
    plt.close(fig)
    log.info("Saved %s", name)


def revenue_trend(orders):
    monthly = kpis.monthly_kpis(orders)
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(monthly["order_month"], monthly["net_revenue"], marker="o", color=ACCENT, linewidth=2)
    ax.fill_between(monthly["order_month"], monthly["net_revenue"], alpha=0.12, color=ACCENT)
    _style(ax, "Monthly net revenue", ylabel="Net revenue ($)")
    ax.set_xticks(ax.get_xticks()[::2])
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    _save(fig, "revenue_trend.png")


def segment_revenue(orders):
    summary = rfm.segment_summary(rfm.segment_customers(orders))
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bars = ax.barh(summary["segment"], summary["revenue"], color=PALETTE[: len(summary)])
    for bar, share in zip(bars, summary["revenue_share_pct"]):
        ax.text(bar.get_width() * 1.01, bar.get_y() + bar.get_height() / 2,
                f"{share}%", va="center", fontsize=9, color=INK)
    ax.invert_yaxis()
    _style(ax, "Revenue by RFM segment", xlabel="Lifetime revenue ($)")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", alpha=0.25)
    _save(fig, "segment_revenue.png")


def retention_heatmap(orders):
    matrix = cohorts.retention_matrix(orders).iloc[:12, :9]
    fig, ax = plt.subplots(figsize=(9, 5))
    im = ax.imshow(matrix.values, cmap="Blues", aspect="auto", vmin=0, vmax=60)
    ax.set_xticks(range(matrix.shape[1]), labels=[f"M{c}" for c in matrix.columns])
    ax.set_yticks(range(matrix.shape[0]), labels=matrix.index)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix.values[i, j]
            if value == value:  # skip NaN
                ax.text(j, i, f"{value:.0f}", ha="center", va="center", fontsize=7,
                        color="white" if value > 35 else INK)
    ax.set_title("Cohort retention (% of cohort active)", fontsize=13, fontweight="bold", color=INK, pad=12)
    ax.tick_params(colors=INK, labelsize=8)
    fig.colorbar(im, ax=ax, shrink=0.8, label="% retained")
    _save(fig, "cohort_retention.png")


def build_all():
    orders = load_orders()
    revenue_trend(orders)
    segment_revenue(orders)
    retention_heatmap(orders)


if __name__ == "__main__":
    build_all()
