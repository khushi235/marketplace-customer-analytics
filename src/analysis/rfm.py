"""RFM segmentation.

Three questions, one row per customer:
    Recency   - how long since they last bought?
    Frequency - how often do they buy?
    Monetary  - how much have they spent?

Each is scored 1-5 by quintile, and the combination maps to a named segment. Quintiles
rather than fixed thresholds, because a threshold that made sense last year is wrong once
the business doubles.
"""

from datetime import datetime
import logging

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

SEGMENT_ACTIONS = {
    "Champions": "Reward, ask for referrals and reviews",
    "Loyal": "Upsell and keep engaged",
    "Potential Loyalists": "Push toward a second purchase",
    "New Customers": "Onboarding sequence",
    "At Risk": "Win-back offer - highest ROI group",
    "Cannot Lose Them": "Personal outreach from account team",
    "Hibernating": "Low-cost reactivation only",
    "Lost": "Suppress from paid campaigns",
}


def build_rfm_table(orders: pd.DataFrame, snapshot_date: datetime = None) -> pd.DataFrame:
    """Collapse the order log into one row per customer."""
    snapshot_date = snapshot_date or orders["order_date"].max() + pd.Timedelta(days=1)

    rfm = (
        orders.groupby("customer_id")
        .agg(
            last_order=("order_date", "max"),
            frequency=("order_id", "nunique"),
            monetary=("net_revenue", "sum"),
            avg_order_value=("net_revenue", "mean"),
        )
        .reset_index()
    )
    rfm["recency_days"] = (snapshot_date - rfm["last_order"]).dt.days
    rfm["monetary"] = rfm["monetary"].round(2)
    rfm["avg_order_value"] = rfm["avg_order_value"].round(2)
    return rfm


def _quintile_score(series: pd.Series, reverse: bool = False) -> pd.Series:
    """Rank into 5 buckets. `rank(method='first')` avoids the duplicate-edge error you get
    with qcut when many customers share the same value (very common for frequency)."""
    ranked = series.rank(method="first", ascending=not reverse)
    return pd.qcut(ranked, 5, labels=[1, 2, 3, 4, 5]).astype(int)


def score_rfm(rfm: pd.DataFrame) -> pd.DataFrame:
    out = rfm.copy()
    out["r_score"] = _quintile_score(out["recency_days"], reverse=True)
    out["f_score"] = _quintile_score(out["frequency"])
    out["m_score"] = _quintile_score(out["monetary"])
    out["rfm_cell"] = out["r_score"].astype(str) + out["f_score"].astype(str) + out["m_score"].astype(str)
    out["rfm_score"] = ((out["r_score"] + out["f_score"] + out["m_score"]) / 3).round(2)
    return out


def assign_segment(row) -> str:
    r, f, m = row["r_score"], row["f_score"], row["m_score"]
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    if r >= 3 and f >= 3:
        return "Loyal"
    if r >= 4 and f <= 2 and m <= 3:
        return "New Customers"
    if r >= 3 and f <= 3:
        return "Potential Loyalists"
    if r <= 2 and f >= 4 and m >= 4:
        return "Cannot Lose Them"
    if r <= 2 and f >= 3:
        return "At Risk"
    if r <= 2 and f <= 2 and m >= 3:
        return "Hibernating"
    return "Lost"


def segment_customers(orders: pd.DataFrame, snapshot_date: datetime = None) -> pd.DataFrame:
    rfm = score_rfm(build_rfm_table(orders, snapshot_date))
    rfm["segment"] = rfm.apply(assign_segment, axis=1)
    rfm["recommended_action"] = rfm["segment"].map(SEGMENT_ACTIONS)
    log.info("Segmented %s customers into %s groups", len(rfm), rfm["segment"].nunique())
    return rfm


def segment_summary(segmented: pd.DataFrame) -> pd.DataFrame:
    """The table the first dashboard page is built from."""
    summary = (
        segmented.groupby("segment")
        .agg(
            customers=("customer_id", "count"),
            revenue=("monetary", "sum"),
            avg_order_value=("avg_order_value", "mean"),
            avg_recency_days=("recency_days", "mean"),
            avg_frequency=("frequency", "mean"),
        )
        .reset_index()
    )
    summary["customer_share_pct"] = (100 * summary["customers"] / summary["customers"].sum()).round(1)
    summary["revenue_share_pct"] = (100 * summary["revenue"] / summary["revenue"].sum()).round(1)
    summary["revenue"] = summary["revenue"].round(2)
    summary["avg_order_value"] = summary["avg_order_value"].round(2)
    summary["avg_recency_days"] = summary["avg_recency_days"].round(0)
    summary["avg_frequency"] = summary["avg_frequency"].round(2)
    return summary.sort_values("revenue", ascending=False).reset_index(drop=True)


def revenue_concentration(segmented: pd.DataFrame, top_pct: float = 0.20) -> dict:
    """How much revenue sits with the top X% of customers - the headline finding."""
    ordered = segmented.sort_values("monetary", ascending=False)
    cutoff = max(1, int(np.ceil(len(ordered) * top_pct)))
    top_revenue = ordered.head(cutoff)["monetary"].sum()
    return {
        "top_customer_pct": round(top_pct * 100, 1),
        "customers": cutoff,
        "revenue_share_pct": round(100 * top_revenue / ordered["monetary"].sum(), 1),
    }
