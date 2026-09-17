-- ============================================================================
-- 02_customer_metrics.sql
-- Purpose : one row per customer with every metric the business argues about,
--           defined once, here.
-- ============================================================================

DROP TABLE IF EXISTS analytics.customer_metrics;

CREATE TABLE analytics.customer_metrics AS
WITH order_level AS (
    SELECT
        customer_id,
        order_id,
        order_date,
        SUM(net_revenue)  AS order_value,
        SUM(gross_margin) AS order_margin
    FROM analytics.stg_orders
    GROUP BY 1, 2, 3
),
per_customer AS (
    SELECT
        customer_id,
        MIN(order_date)                          AS first_order_date,
        MAX(order_date)                          AS last_order_date,
        COUNT(DISTINCT order_id)                 AS order_count,
        ROUND(SUM(order_value), 2)               AS lifetime_revenue,
        ROUND(SUM(order_margin), 2)              AS lifetime_margin,
        ROUND(AVG(order_value), 2)               AS avg_order_value,
        ROUND(MAX(order_value), 2)               AS largest_order
    FROM order_level
    GROUP BY 1
),
gaps AS (
    -- Average days between orders tells us when "quiet" becomes "churned"
    SELECT
        customer_id,
        ROUND(AVG(days_between), 1) AS avg_days_between_orders
    FROM (
        SELECT
            customer_id,
            order_date - LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date) AS days_between
        FROM order_level
    ) t
    WHERE days_between IS NOT NULL
    GROUP BY 1
)
SELECT
    p.customer_id,
    p.first_order_date,
    p.last_order_date,
    DATE_TRUNC('month', p.first_order_date)::DATE            AS cohort_month,
    (CURRENT_DATE - p.last_order_date)                       AS recency_days,
    p.order_count,
    p.lifetime_revenue,
    p.lifetime_margin,
    p.avg_order_value,
    p.largest_order,
    g.avg_days_between_orders,
    CASE WHEN p.order_count > 1 THEN TRUE ELSE FALSE END     AS is_repeat_customer,
    CASE
        WHEN p.order_count > 1
         AND (SELECT MIN(o2.order_date) FROM order_level o2
              WHERE o2.customer_id = p.customer_id
                AND o2.order_date > p.first_order_date) - p.first_order_date <= 45
        THEN TRUE ELSE FALSE
    END                                                      AS second_order_within_45d
FROM per_customer p
LEFT JOIN gaps g ON g.customer_id = p.customer_id;

CREATE INDEX idx_customer_metrics_cohort ON analytics.customer_metrics (cohort_month);
