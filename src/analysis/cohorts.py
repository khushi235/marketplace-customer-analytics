"""Cohort analysis.

A cohort is everyone whose first order landed in the same month. Tracking cohorts instead
of a single churn number separates "we are losing customers" from "we simply acquired
fewer this month" - two problems with completely different fixes.
"""

import logging

import pandas as pd

log = logging.getLogger(__name__)


def add_cohort_columns(orders: pd.DataFrame) -> pd.DataFrame:
    out = orders.copy()
    out["order_month"] = out["order_date"].dt.to_period("M")
    out["cohort_month"] = out.groupby("customer_id")["order_date"].transform("min").dt.to_period("M")
    out["month_index"] = (out["order_month"] - out["cohort_month"]).apply(lambda x: x.n)
    return out


def retention_matrix(orders: pd.DataFrame, max_months: int = 12) -> pd.DataFrame:
    """Rows = cohort, columns = months since first order, values = % still active."""
    data = add_cohort_columns(orders)
    data = data[data["month_index"].between(0, max_months)]

    active = (
        data.groupby(["cohort_month", "month_index"])["customer_id"]
        .nunique()
        .reset_index(name="active_customers")
    )
    sizes = active[active["month_index"] == 0][["cohort_month", "active_customers"]].rename(
        columns={"active_customers": "cohort_size"}
    )
    merged = active.merge(sizes, on="cohort_month")
    merged["retention_pct"] = (100 * merged["active_customers"] / merged["cohort_size"]).round(1)

    matrix = merged.pivot(index="cohort_month", columns="month_index", values="retention_pct")
    matrix.index = matrix.index.astype(str)
    return matrix


def revenue_cohorts(orders: pd.DataFrame, max_months: int = 12) -> pd.DataFrame:
    """Same shape, but cumulative revenue per acquired customer - the LTV curve."""
    data = add_cohort_columns(orders)
    data = data[data["month_index"].between(0, max_months)]

    revenue = (
        data.groupby(["cohort_month", "month_index"])["net_revenue"].sum().reset_index()
    )
    sizes = (
        data[data["month_index"] == 0]
        .groupby("cohort_month")["customer_id"]
        .nunique()
        .reset_index(name="cohort_size")
    )
    merged = revenue.merge(sizes, on="cohort_month").sort_values(["cohort_month", "month_index"])
    merged["cumulative_revenue"] = merged.groupby("cohort_month")["net_revenue"].cumsum()
    merged["ltv_per_customer"] = (merged["cumulative_revenue"] / merged["cohort_size"]).round(2)

    matrix = merged.pivot(index="cohort_month", columns="month_index", values="ltv_per_customer")
    matrix.index = matrix.index.astype(str)
    return matrix


def second_purchase_window(orders: pd.DataFrame, window_days: int = 45) -> pd.DataFrame:
    """Do customers who reorder quickly retain better? (In this data: yes, clearly.)"""
    data = orders.copy()

    # Collapse to one date per order first - order lines would double count the gap
    order_dates = (
        data.groupby(["customer_id", "order_id"])["order_date"].min().reset_index()
    ).sort_values(["customer_id", "order_date"])
    order_dates["order_rank"] = order_dates.groupby("customer_id")["order_date"].rank(method="first")
    first_two = order_dates[order_dates["order_rank"] <= 2]

    gaps = (
        first_two.groupby("customer_id")["order_date"]
        .agg(["min", "max", "count"])
        .reset_index()
    )
    gaps["days_to_second"] = (gaps["max"] - gaps["min"]).dt.days
    gaps["fast_second_purchase"] = (gaps["count"] > 1) & (gaps["days_to_second"] <= window_days)

    lifetime = data.groupby("customer_id").agg(
        orders=("order_id", "nunique"), revenue=("net_revenue", "sum")
    )
    joined = gaps.merge(lifetime, on="customer_id")

    return (
        joined.groupby("fast_second_purchase")
        .agg(
            customers=("customer_id", "count"),
            avg_lifetime_orders=("orders", "mean"),
            avg_lifetime_revenue=("revenue", "mean"),
        )
        .round(2)
        .reset_index()
    )
