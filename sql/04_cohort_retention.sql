-- ============================================================================
-- 04_cohort_retention.sql
-- Purpose : monthly signup cohorts, tracked for 12 months.
-- Reads   : "of the customers who first bought in March, what % came back in
--            month 3, and how much did they spend?"
-- ============================================================================

DROP TABLE IF EXISTS analytics.cohort_retention;

CREATE TABLE analytics.cohort_retention AS
WITH first_purchase AS (
    SELECT
        customer_id,
        DATE_TRUNC('month', MIN(order_date))::DATE AS cohort_month
    FROM analytics.stg_orders
    GROUP BY 1
),
activity AS (
    SELECT
        f.cohort_month,
        o.customer_id,
        DATE_TRUNC('month', o.order_date)::DATE AS activity_month,
        o.net_revenue
    FROM analytics.stg_orders o
    JOIN first_purchase f USING (customer_id)
),
indexed AS (
    SELECT
        cohort_month,
        activity_month,
        customer_id,
        net_revenue,
        (DATE_PART('year',  activity_month) - DATE_PART('year',  cohort_month)) * 12
      + (DATE_PART('month', activity_month) - DATE_PART('month', cohort_month)) AS month_index
    FROM activity
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_customers
    FROM first_purchase
    GROUP BY 1
)
SELECT
    i.cohort_month,
    i.month_index::INT                                          AS month_index,
    cs.cohort_customers,
    COUNT(DISTINCT i.customer_id)                               AS active_customers,
    ROUND(100.0 * COUNT(DISTINCT i.customer_id) / cs.cohort_customers, 1) AS retention_pct,
    ROUND(SUM(i.net_revenue), 2)                                AS cohort_revenue,
    ROUND(SUM(i.net_revenue) / cs.cohort_customers, 2)          AS revenue_per_cohort_customer
FROM indexed i
JOIN cohort_size cs USING (cohort_month)
WHERE i.month_index BETWEEN 0 AND 12
GROUP BY i.cohort_month, i.month_index, cs.cohort_customers
ORDER BY i.cohort_month, month_index;
