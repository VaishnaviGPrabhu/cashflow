-- Analytics queries on the star schema. Each block starts with "-- name: <id>".
-- Run one:  python -m warehouse.queries <id>      Run all:  python -m warehouse.queries

-- name: monthly_cashflow_running_balance
-- Window function: running balance of cash by month.
SELECT d.year_month,
       SUM(CASE WHEN f.direction = 'inflow'  THEN f.amount ELSE 0 END) AS inflow,
       SUM(CASE WHEN f.direction = 'outflow' THEN f.amount ELSE 0 END) AS outflow,
       (SELECT CAST(value AS REAL) FROM ref_settings WHERE key = 'starting_cash')
         + SUM(SUM(f.signed_amount)) OVER (ORDER BY d.year_month) AS closing_cash
FROM fact_transactions f
JOIN dim_date d ON d.date_key = f.date_key
GROUP BY d.year_month
ORDER BY d.year_month;

-- name: revenue_month_over_month
-- LAG(): month-over-month revenue change and growth %.
WITH revenue AS (
    SELECT d.year_month, SUM(f.amount) AS revenue
    FROM fact_transactions f
    JOIN dim_date d     ON d.date_key = f.date_key
    JOIN dim_category c ON c.category_key = f.category_key
    WHERE c.category_group = 'Revenue'
    GROUP BY d.year_month
)
SELECT year_month,
       revenue,
       revenue - LAG(revenue) OVER (ORDER BY year_month) AS change_vs_prev_month,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY year_month))
             / LAG(revenue) OVER (ORDER BY year_month), 2) AS growth_pct
FROM revenue
ORDER BY year_month;

-- name: top_vendors_by_spend
-- Aggregation + RANK() + share of total (window over the whole result).
SELECT vendor, category_name, total_spend, share_of_outflow_pct, spend_rank
FROM vw_vendor_spend
ORDER BY spend_rank
LIMIT 10;

-- name: spend_by_category_pivot
-- Conditional aggregation (pivot): one column per month for outflow categories.
SELECT c.category_name,
       SUM(CASE WHEN d.year_month = '2026-08' THEN f.amount ELSE 0 END) AS aug_2026,
       SUM(CASE WHEN d.year_month = '2026-09' THEN f.amount ELSE 0 END) AS sep_2026,
       SUM(CASE WHEN d.year_month = '2026-10' THEN f.amount ELSE 0 END) AS oct_2026
FROM fact_transactions f
JOIN dim_date d     ON d.date_key = f.date_key
JOIN dim_category c ON c.category_key = f.category_key
WHERE f.direction = 'outflow'
GROUP BY c.category_name
ORDER BY oct_2026 DESC;

-- name: vendor_cost_growth
-- CTE + self-join: each vendor's first vs latest monthly spend.
WITH monthly AS (
    SELECT p.counterparty_name AS vendor, d.year_month, SUM(f.amount) AS spend
    FROM fact_transactions f
    JOIN dim_counterparty p ON p.counterparty_key = f.counterparty_key
    JOIN dim_date d         ON d.date_key = f.date_key
    WHERE f.direction = 'outflow'
    GROUP BY p.counterparty_name, d.year_month
),
bounds AS (
    SELECT vendor, MIN(year_month) AS first_month, MAX(year_month) AS last_month FROM monthly GROUP BY vendor
)
SELECT b.vendor, b.first_month, m1.spend AS first_spend, b.last_month, m2.spend AS last_spend,
       ROUND(100.0 * (m2.spend - m1.spend) / m1.spend, 1) AS growth_pct
FROM bounds b
JOIN monthly m1 ON m1.vendor = b.vendor AND m1.year_month = b.first_month
JOIN monthly m2 ON m2.vendor = b.vendor AND m2.year_month = b.last_month
WHERE b.first_month <> b.last_month
ORDER BY growth_pct DESC;

-- name: receivables_aging_summary
-- GROUP BY on a view: open invoices by aging bucket.
SELECT aging_bucket, COUNT(*) AS invoices, SUM(amount) AS amount
FROM vw_receivables_aging
GROUP BY aging_bucket
ORDER BY MIN(days_past_due);

-- name: payables_vs_cash
-- Subquery: do the next 30 days of payables fit inside current cash?
SELECT (SELECT SUM(amount) FROM vw_payables_due WHERE days_until_due <= 30) AS payables_due_30d,
       (SELECT current_cash FROM vw_runway)                                  AS current_cash,
       (SELECT current_cash FROM vw_runway)
         - COALESCE((SELECT SUM(amount) FROM vw_payables_due WHERE days_until_due <= 30), 0) AS cash_after_payables;

-- name: outflow_moving_average
-- Window frame: 3-month moving average of outflows.
WITH monthly AS (
    SELECT d.year_month, SUM(f.amount) AS outflow
    FROM fact_transactions f
    JOIN dim_date d ON d.date_key = f.date_key
    WHERE f.direction = 'outflow'
    GROUP BY d.year_month
)
SELECT year_month, outflow,
       ROUND(AVG(outflow) OVER (ORDER BY year_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS moving_avg_3m
FROM monthly
ORDER BY year_month;

-- name: unusual_transactions
-- Correlated subquery: outflows above 2x that vendor's own average (spike detection).
SELECT d.full_date, p.counterparty_name AS vendor, c.category_name, f.amount,
       ROUND((SELECT AVG(f2.amount) FROM fact_transactions f2
              WHERE f2.counterparty_key = f.counterparty_key AND f2.direction = 'outflow'), 2) AS vendor_avg
FROM fact_transactions f
JOIN dim_date d         ON d.date_key = f.date_key
JOIN dim_counterparty p ON p.counterparty_key = f.counterparty_key
JOIN dim_category c     ON c.category_key = f.category_key
WHERE f.direction = 'outflow'
  AND f.amount > 2 * (SELECT AVG(f2.amount) FROM fact_transactions f2
                      WHERE f2.counterparty_key = f.counterparty_key AND f2.direction = 'outflow')
ORDER BY f.amount DESC;

-- name: actual_vs_planned_revenue
-- Join facts to plan: where actuals and plan overlap, how far apart are they?
SELECT d.year_month,
       p.expected_revenue,
       (SELECT SUM(f.amount) FROM fact_transactions f
        JOIN dim_date fd ON fd.date_key = f.date_key
        WHERE f.direction = 'inflow' AND fd.year_month = d.year_month) AS actual_revenue
FROM fact_revenue_plan p
JOIN dim_date d ON d.date_key = p.month_date_key
ORDER BY d.year_month;

-- name: hiring_plan_cumulative_cost
-- Window: cumulative extra payroll from the hiring plan.
SELECT d.year_month, h.role, h.headcount, h.monthly_cost,
       SUM(h.monthly_cost) OVER (ORDER BY d.full_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_monthly_cost
FROM fact_hiring_plan h
JOIN dim_date d ON d.date_key = h.month_date_key
ORDER BY d.full_date;
