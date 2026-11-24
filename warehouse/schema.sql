-- Star schema for the AI CashFlow warehouse (SQLite).
-- Layers: stg_* (raw copy of the latest extract) -> dim_* / fact_* (clean, modelled)
-- plus operational tables that record every pipeline run.

-- ---------- Dimensions ----------
CREATE TABLE IF NOT EXISTS dim_date (
    date_key     INTEGER PRIMARY KEY,           -- yyyymmdd
    full_date    TEXT    NOT NULL UNIQUE,       -- yyyy-mm-dd
    year         INTEGER NOT NULL,
    quarter      INTEGER NOT NULL,
    month        INTEGER NOT NULL,
    month_name   TEXT    NOT NULL,
    year_month   TEXT    NOT NULL,              -- yyyy-mm
    day          INTEGER NOT NULL,
    day_of_week  INTEGER NOT NULL,              -- 0 = Monday
    day_name     TEXT    NOT NULL,
    is_weekend   INTEGER NOT NULL CHECK (is_weekend IN (0, 1))
);

CREATE TABLE IF NOT EXISTS dim_counterparty (
    counterparty_key  INTEGER PRIMARY KEY AUTOINCREMENT,
    counterparty_name TEXT NOT NULL UNIQUE,
    counterparty_type TEXT NOT NULL CHECK (counterparty_type IN ('customer', 'vendor'))
);

CREATE TABLE IF NOT EXISTS dim_category (
    category_key   INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name  TEXT NOT NULL UNIQUE,
    category_group TEXT NOT NULL CHECK (category_group IN ('Revenue', 'People', 'Operating'))
);

-- ---------- Facts ----------
-- Event table: append-only, loaded incrementally. row_hash makes re-runs idempotent.
CREATE TABLE IF NOT EXISTS fact_transactions (
    transaction_key  INTEGER PRIMARY KEY AUTOINCREMENT,
    row_hash         TEXT    NOT NULL UNIQUE,
    date_key         INTEGER NOT NULL REFERENCES dim_date (date_key),
    counterparty_key INTEGER NOT NULL REFERENCES dim_counterparty (counterparty_key),
    category_key     INTEGER NOT NULL REFERENCES dim_category (category_key),
    direction        TEXT    NOT NULL CHECK (direction IN ('inflow', 'outflow')),
    amount           REAL    NOT NULL CHECK (amount >= 0),
    signed_amount    REAL    NOT NULL,          -- +inflow / -outflow
    first_run_id     TEXT    NOT NULL,
    last_run_id      TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_fact_txn_date     ON fact_transactions (date_key);
CREATE INDEX IF NOT EXISTS ix_fact_txn_party    ON fact_transactions (counterparty_key);
CREATE INDEX IF NOT EXISTS ix_fact_txn_category ON fact_transactions (category_key);

-- Snapshot tables: fully reloaded on every run (the source is a current-state list).
CREATE TABLE IF NOT EXISTS fact_receivables (
    receivable_key   INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_date_key INTEGER NOT NULL REFERENCES dim_date (date_key),
    due_date_key     INTEGER NOT NULL REFERENCES dim_date (date_key),
    counterparty_key INTEGER NOT NULL REFERENCES dim_counterparty (counterparty_key),
    amount           REAL    NOT NULL CHECK (amount >= 0),
    status           TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_payables (
    payable_key      INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_date_key INTEGER NOT NULL REFERENCES dim_date (date_key),
    due_date_key     INTEGER NOT NULL REFERENCES dim_date (date_key),
    counterparty_key INTEGER NOT NULL REFERENCES dim_counterparty (counterparty_key),
    amount           REAL    NOT NULL CHECK (amount >= 0),
    status           TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_recurring_expenses (
    counterparty_key INTEGER NOT NULL REFERENCES dim_counterparty (counterparty_key),
    category_key     INTEGER NOT NULL REFERENCES dim_category (category_key),
    monthly_amount   REAL    NOT NULL CHECK (monthly_amount >= 0),
    PRIMARY KEY (counterparty_key, category_key)
);

CREATE TABLE IF NOT EXISTS fact_payroll (
    employee_id    TEXT PRIMARY KEY,
    role           TEXT NOT NULL,
    start_date_key INTEGER NOT NULL REFERENCES dim_date (date_key),
    monthly_salary REAL NOT NULL CHECK (monthly_salary >= 0)
);

CREATE TABLE IF NOT EXISTS fact_revenue_plan (
    month_date_key   INTEGER PRIMARY KEY REFERENCES dim_date (date_key),
    expected_revenue REAL NOT NULL CHECK (expected_revenue >= 0)
);

CREATE TABLE IF NOT EXISTS fact_hiring_plan (
    plan_key       INTEGER PRIMARY KEY AUTOINCREMENT,
    month_date_key INTEGER NOT NULL REFERENCES dim_date (date_key),
    role           TEXT    NOT NULL,
    headcount      INTEGER NOT NULL CHECK (headcount >= 0),
    monthly_salary REAL    NOT NULL CHECK (monthly_salary >= 0),
    monthly_cost   REAL    NOT NULL                -- headcount * monthly_salary
);

-- ---------- Reference + operational tables ----------
CREATE TABLE IF NOT EXISTS ref_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS etl_run_log (
    run_id         TEXT PRIMARY KEY,
    started_at     TEXT NOT NULL,
    finished_at    TEXT,
    status         TEXT NOT NULL CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED')),
    rows_extracted INTEGER NOT NULL DEFAULT 0,
    rows_loaded    INTEGER NOT NULL DEFAULT 0,
    rows_rejected  INTEGER NOT NULL DEFAULT 0,
    message        TEXT
);

CREATE TABLE IF NOT EXISTS dq_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id    TEXT NOT NULL,
    check_name TEXT NOT NULL,
    dataset   TEXT NOT NULL,
    severity  TEXT NOT NULL,
    passed    INTEGER NOT NULL CHECK (passed IN (0, 1)),
    details   TEXT
);

CREATE TABLE IF NOT EXISTS etl_rejects (
    reject_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     TEXT NOT NULL,
    dataset    TEXT NOT NULL,
    reason     TEXT NOT NULL,
    raw_record TEXT NOT NULL
);
