"""Tests for cohort logic.

The month index is the easy thing to get wrong (year boundaries, customers with a single
order), and a wrong index quietly shifts the whole retention curve.
"""

import pandas as pd
import pytest

from src.analysis.cohorts import add_cohort_columns, retention_matrix, second_purchase_window


@pytest.fixture
def orders():
    return pd.DataFrame(
        [
            # Customer A: signs up Nov 2023, comes back in Jan 2024 (crosses the year end)
            {"order_id": "O1", "customer_id": "A", "order_date": pd.Timestamp("2023-11-10"), "net_revenue": 100.0},
            {"order_id": "O2", "customer_id": "A", "order_date": pd.Timestamp("2024-01-15"), "net_revenue": 120.0},
            # Customer B: two orders 20 days apart - a fast second purchase
            {"order_id": "O3", "customer_id": "B", "order_date": pd.Timestamp("2023-11-05"), "net_revenue": 80.0},
            {"order_id": "O4", "customer_id": "B", "order_date": pd.Timestamp("2023-11-25"), "net_revenue": 95.0},
            {"order_id": "O5", "customer_id": "B", "order_date": pd.Timestamp("2024-02-01"), "net_revenue": 200.0},
            # Customer C: one order only
            {"order_id": "O6", "customer_id": "C", "order_date": pd.Timestamp("2023-11-20"), "net_revenue": 60.0},
        ]
    )


def test_month_index_handles_the_year_boundary(orders):
    data = add_cohort_columns(orders)
    customer_a = data[data["customer_id"] == "A"].sort_values("order_date")
    assert list(customer_a["month_index"]) == [0, 2]


def test_every_customer_starts_at_month_zero(orders):
    data = add_cohort_columns(orders)
    assert data.groupby("customer_id")["month_index"].min().eq(0).all()


def test_retention_matrix_starts_at_100_percent(orders):
    matrix = retention_matrix(orders)
    assert (matrix[0] == 100.0).all()


def test_retention_never_exceeds_100_percent(orders):
    matrix = retention_matrix(orders)
    assert matrix.max().max() <= 100.0


def test_fast_second_purchase_is_detected(orders):
    result = second_purchase_window(orders, window_days=45)
    fast = result[result["fast_second_purchase"]]
    assert int(fast["customers"].iloc[0]) == 1  # only customer B


def test_fast_buyers_have_higher_lifetime_value(orders):
    result = second_purchase_window(orders, window_days=45).set_index("fast_second_purchase")
    assert result.loc[True, "avg_lifetime_revenue"] > result.loc[False, "avg_lifetime_revenue"]
