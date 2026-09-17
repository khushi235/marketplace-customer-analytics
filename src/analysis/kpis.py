"""The KPI layer.

Every metric the business reports on is defined exactly once, here. Before this existed,
marketing, finance and ops each had their own version of "revenue" and monthly reviews
started with an argument about whose number was right.
"""

import pandas as pd

KPI_DEFINITIONS = {
    "net_revenue": "Quantity x unit price, minus discounts. Excludes cancelled and test orders.",
    "gross_margin": "Net revenue minus cost of goods.",
    "aov": "Net revenue divided by distinct orders (not by order lines).",
    "repeat_rate": "Share of customers with more than one order in the period.",
    "conversion_rate": "Orders divided by sessions, from the web analytics feed.",
    "revenue_per_customer": "Net revenue divided by distinct active customers.",
}


def monthly_kpis(orders: pd.DataFrame) -> pd.DataFrame:
    data = orders.copy()
    data["order_month"] = data["order_date"].dt.to_period("M").astype(str)

    kpis = (
        data.groupby("order_month")
        .agg(
            orders=("order_id", "nunique"),
            customers=("customer_id", "nunique"),
            net_revenue=("net_revenue", "sum"),
            gross_margin=("gross_margin", "sum"),
            units=("quantity", "sum"),
        )
        .reset_index()
    )
    kpis["aov"] = (kpis["net_revenue"] / kpis["orders"]).round(2)
    kpis["revenue_per_customer"] = (kpis["net_revenue"] / kpis["customers"]).round(2)
    kpis["margin_pct"] = (100 * kpis["gross_margin"] / kpis["net_revenue"]).round(1)
    kpis["revenue_mom_pct"] = (100 * kpis["net_revenue"].pct_change()).round(1)
    kpis["net_revenue"] = kpis["net_revenue"].round(2)
    kpis["gross_margin"] = kpis["gross_margin"].round(2)
    return kpis


def repeat_rate(orders: pd.DataFrame) -> float:
    per_customer = orders.groupby("customer_id")["order_id"].nunique()
    return round(100 * (per_customer > 1).mean(), 1)


def category_performance(orders: pd.DataFrame) -> pd.DataFrame:
    perf = (
        orders.groupby("category")
        .agg(
            orders=("order_id", "nunique"),
            net_revenue=("net_revenue", "sum"),
            gross_margin=("gross_margin", "sum"),
            units=("quantity", "sum"),
        )
        .reset_index()
    )
    perf["margin_pct"] = (100 * perf["gross_margin"] / perf["net_revenue"]).round(1)
    perf["revenue_share_pct"] = (100 * perf["net_revenue"] / perf["net_revenue"].sum()).round(1)
    perf["net_revenue"] = perf["net_revenue"].round(2)
    perf["gross_margin"] = perf["gross_margin"].round(2)
    return perf.sort_values("net_revenue", ascending=False).reset_index(drop=True)


def channel_performance(orders: pd.DataFrame) -> pd.DataFrame:
    perf = (
        orders.groupby("channel")
        .agg(
            orders=("order_id", "nunique"),
            customers=("customer_id", "nunique"),
            net_revenue=("net_revenue", "sum"),
        )
        .reset_index()
    )
    perf["aov"] = (perf["net_revenue"] / perf["orders"]).round(2)
    perf["net_revenue"] = perf["net_revenue"].round(2)
    return perf.sort_values("net_revenue", ascending=False).reset_index(drop=True)


def headline_summary(orders: pd.DataFrame) -> dict:
    """The five numbers that go at the top of the dashboard."""
    return {
        "total_net_revenue": round(float(orders["net_revenue"].sum()), 2),
        "total_orders": int(orders["order_id"].nunique()),
        "total_customers": int(orders["customer_id"].nunique()),
        "aov": round(float(orders["net_revenue"].sum() / orders["order_id"].nunique()), 2),
        "repeat_rate_pct": repeat_rate(orders),
        "margin_pct": round(100 * float(orders["gross_margin"].sum() / orders["net_revenue"].sum()), 1),
    }
