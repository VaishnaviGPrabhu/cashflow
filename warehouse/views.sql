-- Reporting views: the layer that the API, the web page and Power BI read from.

DROP VIEW IF EXISTS vw_monthly_cashflow;
CREATE VIEW vw_monthly_cashflow AS
WITH monthly AS (
    SELECT d.year_month,
           ROUND(SUM(CASE WHEN f.direction = 'inflow'  THEN f.amount ELSE 0 END), 2) AS inflow,
           ROUND(SUM(CASE WHEN f.direction = 'outflow' THEN f.amount ELSE 0 END), 2) AS outflow
    FROM fact_transactions f
    JOIN dim_date d ON d.date_key = f.date_key
    GROUP BY d.year_month
)
SELECT year_month,
       inflow,
       outflow,
       ROUND(inflow - outflow, 2) AS net_cash_flow,
       ROUND((SELECT CAST(value AS REAL) FROM ref_settings WHERE key = 'starting_cash')
             + SUM(inflow - outflow) OVER (ORDER BY year_month
                                           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS closing_cash
FROM monthly;

DROP VIEW IF EXISTS vw_category_monthly;
CREATE VIEW vw_category_monthly AS
SELECT d.year_month,
       c.category_name,
       c.category_group,
       f.direction,
       ROUND(SUM(f.amount), 2) AS amount,
       COUNT(*)                AS txn_count
FROM fact_transactions f
JOIN dim_date d     ON d.date_key = f.date_key
JOIN dim_category c ON c.category_key = f.category_key
GROUP BY d.year_month, c.category_name, c.category_group, f.direction;

DROP VIEW IF EXISTS vw_vendor_spend;
CREATE VIEW vw_vendor_spend AS
WITH spend AS (
    SELECT p.counterparty_name AS vendor,
           c.category_name,
           ROUND(SUM(f.amount), 2) AS total_spend,
           COUNT(*)                AS txn_count
    FROM fact_transactions f
    JOIN dim_counterparty p ON p.counterparty_key = f.counterparty_key
    JOIN dim_category c     ON c.category_key = f.category_key
    WHERE f.direction = 'outflow'
    GROUP BY p.counterparty_name, c.category_name
)
SELECT vendor,
       category_name,
       total_spend,
       txn_count,
       ROUND(100.0 * total_spend / SUM(total_spend) OVER (), 2) AS share_of_outflow_pct,
       RANK() OVER (ORDER BY total_spend DESC)                  AS spend_rank
FROM spend;

DROP VIEW IF EXISTS vw_receivables_aging;
CREATE VIEW vw_receivables_aging AS
SELECT p.counterparty_name AS customer,
       r.amount,
       r.status,
       d.full_date AS due_date,
       CAST(julianday((SELECT value FROM ref_settings WHERE key = 'as_of_date')) - julianday(d.full_date) AS INTEGER) AS days_past_due,
       CASE
           WHEN julianday((SELECT value FROM ref_settings WHERE key = 'as_of_date')) <= julianday(d.full_date) THEN 'Not yet due'
           WHEN julianday((SELECT value FROM ref_settings WHERE key = 'as_of_date')) - julianday(d.full_date) <= 30 THEN '1-30 days'
           WHEN julianday((SELECT value FROM ref_settings WHERE key = 'as_of_date')) - julianday(d.full_date) <= 60 THEN '31-60 days'
           ELSE '61+ days'
       END AS aging_bucket
FROM fact_receivables r
JOIN dim_counterparty p ON p.counterparty_key = r.counterparty_key
JOIN dim_date d         ON d.date_key = r.due_date_key
WHERE r.status = 'open';

DROP VIEW IF EXISTS vw_payables_due;
CREATE VIEW vw_payables_due AS
SELECT p.counterparty_name AS vendor,
       a.amount,
       a.status,
       d.full_date AS due_date,
       CAST(julianday(d.full_date) - julianday((SELECT value FROM ref_settings WHERE key = 'as_of_date')) AS INTEGER) AS days_until_due
FROM fact_payables a
JOIN dim_counterparty p ON p.counterparty_key = a.counterparty_key
JOIN dim_date d         ON d.date_key = a.due_date_key
WHERE a.status = 'open';

-- Same maths as core/calculations.py (current cash, monthly burn, runway), done in SQL.
DROP VIEW IF EXISTS vw_runway;
CREATE VIEW vw_runway AS
WITH cash AS (
    SELECT (SELECT CAST(value AS REAL) FROM ref_settings WHERE key = 'starting_cash')
           + COALESCE(SUM(signed_amount), 0) AS current_cash
    FROM fact_transactions
),
cost AS (
    SELECT (SELECT COALESCE(SUM(monthly_amount), 0) FROM fact_recurring_expenses)
         + (SELECT COALESCE(SUM(monthly_salary), 0) FROM fact_payroll) AS monthly_cost
),
rev AS (
    SELECT COALESCE(SUM(CASE WHEN f.direction = 'inflow' THEN f.amount END), 0) * 1.0
           / MAX(COUNT(DISTINCT d.year_month), 1) AS avg_monthly_inflow
    FROM fact_transactions f
    JOIN dim_date d ON d.date_key = f.date_key
)
SELECT ROUND(current_cash, 2)                          AS current_cash,
       ROUND(monthly_cost - avg_monthly_inflow, 2)     AS monthly_burn,
       CASE WHEN monthly_cost - avg_monthly_inflow > 0
            THEN ROUND(current_cash / (monthly_cost - avg_monthly_inflow), 4) END AS runway_months
FROM cash, cost, rev;
