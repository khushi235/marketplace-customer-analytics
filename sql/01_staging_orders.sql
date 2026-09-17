-- ============================================================================
-- 01_staging_orders.sql
-- Purpose : one clean, trustworthy order line per transaction.
-- Notes   : the raw feed contains test orders, cancelled orders and duplicate
--           rows caused by a retry bug in the checkout service. All three are
--           removed here so every downstream model agrees on what "an order" is.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS analytics;

DROP TABLE IF EXISTS analytics.stg_orders;

CREATE TABLE analytics.stg_orders AS
WITH deduplicated AS (
    SELECT
        o.*,
        ROW_NUMBER() OVER (
            PARTITION BY o.order_id
            ORDER BY o.updated_at DESC
        ) AS rn
    FROM raw.orders o
),
cleaned AS (
    SELECT
        order_id,
        customer_id,
        CAST(order_date AS DATE)                       AS order_date,
        DATE_TRUNC('month', order_date)::DATE          AS order_month,
        LOWER(TRIM(channel))                           AS channel,
        LOWER(TRIM(category))                          AS category,
        quantity,
        ROUND(unit_price, 2)                           AS unit_price,
        ROUND(discount, 2)                             AS discount,
        ROUND(quantity * unit_price - discount, 2)     AS net_revenue,
        ROUND(cost_of_goods, 2)                        AS cost_of_goods,
        status
    FROM deduplicated
    WHERE rn = 1
      AND status NOT IN ('cancelled', 'test')
      AND quantity > 0
      AND unit_price > 0
      AND customer_id IS NOT NULL
)
SELECT
    c.*,
    ROUND(c.net_revenue - c.cost_of_goods, 2)                       AS gross_margin,
    CASE WHEN c.net_revenue > 0
         THEN ROUND((c.net_revenue - c.cost_of_goods) / c.net_revenue, 4)
    END                                                             AS margin_pct
FROM cleaned c;

CREATE INDEX idx_stg_orders_customer ON analytics.stg_orders (customer_id);
CREATE INDEX idx_stg_orders_date     ON analytics.stg_orders (order_date);

-- Data-quality guardrail: this should always return zero rows.
-- SELECT order_id, COUNT(*) FROM analytics.stg_orders GROUP BY 1 HAVING COUNT(*) > 1;
