"""Tests for the RFM logic.

Segmentation drives real marketing spend, so the boundary cases matter: a customer with
one huge order must not be labelled a Champion, and a dormant big spender must be caught.
"""

import pandas as pd
import pytest

from src.analysis.rfm import (
    assign_segment,
    build_rfm_table,
    revenue_concentration,
    score_rfm,
    segment_customers,
    segment_summary,
)


@pytest.fixture
def orders():
    rows = []
    # 50 customers with deliberately different behaviour patterns
    for i in range(50):
        customer = f"C{i:03d}"
        n_orders = 1 + (i % 8)
        for k in range(n_orders):
            rows.append(
                {
                    "order_id": f"O{i:03d}{k}",
                    "customer_id": customer,
                    "order_date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=i * 5 + k * 20),
                    "net_revenue": 50 + i * 7 + k * 15,
                    "gross_margin": 20 + i * 3,
                    "quantity": 1,
                    "category": "apparel",
                    "channel": "web",
                }
            )
    return pd.DataFrame(rows)


def test_rfm_table_has_one_row_per_customer(orders):
    table = build_rfm_table(orders)
    assert len(table) == orders["customer_id"].nunique()
    assert set(["recency_days", "frequency", "monetary"]).issubset(table.columns)


def test_scores_are_between_one_and_five(orders):
    scored = score_rfm(build_rfm_table(orders))
    for column in ("r_score", "f_score", "m_score"):
        assert scored[column].between(1, 5).all()


def test_recency_is_reversed_so_recent_scores_higher(orders):
    scored = score_rfm(build_rfm_table(orders))
    most_recent = scored.nsmallest(1, "recency_days").iloc[0]
    least_recent = scored.nlargest(1, "recency_days").iloc[0]
    assert most_recent["r_score"] > least_recent["r_score"]


def test_champion_rules():
    assert assign_segment({"r_score": 5, "f_score": 5, "m_score": 5}) == "Champions"
    assert assign_segment({"r_score": 5, "f_score": 1, "m_score": 1}) == "New Customers"
    assert assign_segment({"r_score": 1, "f_score": 5, "m_score": 5}) == "Cannot Lose Them"
    assert assign_segment({"r_score": 1, "f_score": 1, "m_score": 1}) == "Lost"


def test_one_big_order_is_not_a_champion():
    """High monetary value alone must not earn the top segment - frequency matters."""
    assert assign_segment({"r_score": 5, "f_score": 1, "m_score": 5}) != "Champions"


def test_every_customer_gets_a_segment_and_an_action(orders):
    segmented = segment_customers(orders)
    assert segmented["segment"].notna().all()
    assert segmented["recommended_action"].notna().all()


def test_segment_summary_shares_add_to_100(orders):
    summary = segment_summary(segment_customers(orders))
    assert round(summary["customer_share_pct"].sum()) == 100
    assert round(summary["revenue_share_pct"].sum()) == 100


def test_revenue_concentration_is_a_valid_percentage(orders):
    result = revenue_concentration(segment_customers(orders), top_pct=0.20)
    assert 0 < result["revenue_share_pct"] <= 100
    assert result["customers"] == 10
