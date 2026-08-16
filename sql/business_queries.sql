-- 1. Monthly performance. December 2011 is incomplete.
SELECT
    year_month,
    ROUND(SUM(line_value), 2) AS revenue,
    COUNT(DISTINCT invoice_no) AS orders,
    ROUND(SUM(line_value) / COUNT(DISTINCT invoice_no), 2) AS average_order_value
FROM transactions
WHERE is_valid_sale = 1
GROUP BY year_month
ORDER BY year_month;

-- 2. Largest markets outside the UK.
SELECT
    country,
    ROUND(SUM(line_value), 2) AS revenue,
    COUNT(DISTINCT invoice_no) AS orders,
    COUNT(DISTINCT customer_id) AS customers
FROM transactions
WHERE is_valid_sale = 1
  AND country <> 'United Kingdom'
GROUP BY country
ORDER BY revenue DESC
LIMIT 10;

-- 3. Products with enough volume to make the return rate useful.
WITH sales AS (
    SELECT stock_code, MAX(description) AS description, SUM(quantity) AS sold_units
    FROM transactions
    WHERE is_valid_sale = 1
    GROUP BY stock_code
), returns AS (
    SELECT stock_code, ABS(SUM(quantity)) AS return_units
    FROM transactions
    WHERE is_cancellation = 1 AND quantity < 0
    GROUP BY stock_code
)
SELECT
    s.stock_code,
    s.description,
    s.sold_units,
    COALESCE(r.return_units, 0) AS return_units,
    ROUND(100.0 * COALESCE(r.return_units, 0) /
        (s.sold_units + COALESCE(r.return_units, 0)), 2) AS return_unit_rate_pct
FROM sales s
LEFT JOIN returns r USING (stock_code)
WHERE s.sold_units >= 100 AND COALESCE(r.return_units, 0) >= 10
ORDER BY return_unit_rate_pct DESC
LIMIT 15;

-- 4. High-value customers who may need reactivation.
SELECT
    customer_id,
    recency_days,
    frequency,
    ROUND(monetary, 2) AS historical_revenue,
    segment
FROM customer_rfm
WHERE segment = 'At risk'
ORDER BY historical_revenue DESC
LIMIT 25;

-- 5. Revenue concentration by customer decile.
WITH ranked AS (
    SELECT
        customer_id,
        monetary,
        NTILE(10) OVER (ORDER BY monetary DESC) AS customer_decile
    FROM customer_rfm
)
SELECT
    customer_decile,
    COUNT(*) AS customers,
    ROUND(SUM(monetary), 2) AS revenue,
    ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 2) AS revenue_share_pct
FROM ranked
GROUP BY customer_decile
ORDER BY customer_decile;

