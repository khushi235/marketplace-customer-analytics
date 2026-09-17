"""Builds every curated table Power BI and the finance Excel pack read.

This is the whole monthly reporting job. It used to be a day of copy-paste; now it is
`python -m src.reporting.build_report`.
"""

import json
import logging
from pathlib import Path

import pandas as pd

from src.analysis import cohorts, kpis, rfm
from src.db import load_orders

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"


def _write(df: pd.DataFrame, name: str, index: bool = False) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{name}.csv"
    df.to_csv(path, index=index)
    log.info("Wrote %s (%s rows)", path.name, len(df))


def build() -> dict:
    orders = load_orders()
    log.info("Loaded %s order lines covering %s customers", len(orders), orders["customer_id"].nunique())

    headline = kpis.headline_summary(orders)
    _write(kpis.monthly_kpis(orders), "monthly_kpis")
    _write(kpis.category_performance(orders), "category_performance")
    _write(kpis.channel_performance(orders), "channel_performance")

    segmented = rfm.segment_customers(orders)
    _write(segmented, "customer_segments")
    _write(rfm.segment_summary(segmented), "segment_summary")

    _write(cohorts.retention_matrix(orders), "cohort_retention", index=True)
    _write(cohorts.revenue_cohorts(orders), "cohort_ltv", index=True)
    _write(cohorts.second_purchase_window(orders), "second_purchase_effect")

    headline["revenue_concentration"] = rfm.revenue_concentration(segmented)
    with open(REPORTS_DIR / "headline_kpis.json", "w", encoding="utf-8") as fh:
        json.dump(headline, fh, indent=2)

    # Finance still wants one Excel file with every tab. It is easier to give them one
    # than to migrate them, and it takes four lines.
    with pd.ExcelWriter(REPORTS_DIR / "monthly_pack.xlsx", engine="openpyxl") as writer:
        kpis.monthly_kpis(orders).to_excel(writer, sheet_name="KPIs", index=False)
        rfm.segment_summary(segmented).to_excel(writer, sheet_name="Segments", index=False)
        kpis.category_performance(orders).to_excel(writer, sheet_name="Categories", index=False)

    log.info("Headline: %s", headline)
    return headline


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
