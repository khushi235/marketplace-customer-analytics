-- ============================================================================
-- 03_rfm_segments.sql
-- Purpose : RFM scoring in SQL so Power BI can refresh segments without Python.
-- Method  : NTILE(5) ranks customers into quintiles. Quintiles - not fixed
--           thresholds - so the segments stay stable as the business grows.
--           Recency is reversed: fewer days since last order = better score.
-- ============================================================================

DROP TABLE IF EXISTS analytics.rfm_segments;

CREATE TABLE analytics.rfm_segments AS
WITH scored AS (
    SELECT
        customer_id,
        recency_days,
        order_count      AS frequency,
        lifetime_revenue AS monetary,
        NTILE(5) OVER (ORDER BY recency_days DESC)     AS r_score,
        NTILE(5) OVER (ORDER BY order_count ASC)       AS f_score,
        NTILE(5) OVER (ORDER BY lifetime_revenue ASC)  AS m_score
    FROM analytics.customer_metrics
),
labelled AS (
    SELECT
        s.*,
        (r_score::TEXT || f_score::TEXT || m_score::TEXT) AS rfm_cell,
        ROUND((r_score + f_score + m_score) / 3.0, 2)     AS rfm_score,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3                  THEN 'Loyal'
            WHEN r_score >= 4 AND f_score <= 2 AND m_score <= 3  THEN 'New Customers'
            WHEN r_score >= 3 AND f_score <= 3                   THEN 'Potential Loyalists'
            WHEN r_score <= 2 AND f_score >= 4 AND m_score >= 4  THEN 'Cannot Lose Them'
            WHEN r_score <= 2 AND f_score >= 3                   THEN 'At Risk'
            WHEN r_score <= 2 AND f_score <= 2 AND m_score >= 3  THEN 'Hibernating'
            ELSE 'Lost'
        END AS segment
    FROM scored s
)
SELECT
    l.*,
    cm.lifetime_margin,
    cm.avg_order_value,
    cm.cohort_month
FROM labelled l
JOIN analytics.customer_metrics cm USING (customer_id);

-- Segment summary the dashboard's first page is built on.
-- SELECT segment,
--        COUNT(*)                                        AS customers,
--        ROUND(SUM(monetary), 0)                         AS revenue,
--        ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1) AS revenue_share_pct
-- FROM analytics.rfm_segments
-- GROUP BY segment
-- ORDER BY revenue DESC;
