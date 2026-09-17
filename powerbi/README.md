# Power BI dashboard

The `.pbix` file is not committed (it contains a live connection string and it is large).
This folder holds everything needed to rebuild it: the data model, the pages and the DAX.

## Data model

A simple star schema — one fact table, four dimensions. Keeping it star-shaped is what
makes the report fast; an early version joined everything into one flat table and the
slicers took seconds to respond.

```
            ┌───────────────┐
            │  dim_date     │
            └──────┬────────┘
                   │
┌────────────┐   ┌─┴──────────────┐   ┌─────────────────┐
│ dim_product│───│  fct_orders    │───│ dim_customer    │
└────────────┘   └─┬──────────────┘   └────────┬────────┘
                   │                            │
            ┌──────┴────────┐          ┌────────┴────────┐
            │ dim_channel   │          │ rfm_segments    │
            └───────────────┘          └─────────────────┘
```

| Table | Source | Grain |
| --- | --- | --- |
| `fct_orders` | `analytics.stg_orders` | one row per order line |
| `dim_customer` | `analytics.customer_metrics` | one row per customer |
| `rfm_segments` | `analytics.rfm_segments` | one row per customer |
| `cohort_retention` | `analytics.cohort_retention` | cohort x month index |
| `dim_date` | generated in Power Query | one row per day |

## Pages

**1. Executive summary**
KPI cards (revenue, orders, AOV, margin %, repeat rate), revenue trend with MoM %,
revenue by channel, and a target-vs-actual gauge.

**2. Customer segments**
Segment treemap sized by revenue, segment table with customers / revenue / share, and the
recommended action per segment so the marketing team can act without asking an analyst.

**3. Retention & cohorts**
Cohort heatmap (retention %), LTV curve by cohort, and the second-purchase-window
comparison that showed fast repeat buyers retain roughly 3x better.

**4. Product & category**
Category revenue and margin, top and bottom SKUs, and a margin-vs-volume scatter that
surfaces high-volume, low-margin products.

## Refresh

- Scheduled refresh runs daily at 06:00 against the `analytics` schema.
- Incremental refresh on `fct_orders`: last 3 months refreshed, older partitions archived.
- Row-level security: regional managers only see their own region.

## Things I'd flag in a review

- Power Query does almost nothing — all transformation happens upstream in SQL. That is
  deliberate: transformations in Power Query are invisible to everyone who is not in the
  file, and they cannot be tested.
- Measures are written once and reused. No calculated columns where a measure will do.
