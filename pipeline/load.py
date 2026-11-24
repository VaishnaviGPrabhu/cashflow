"""Load step: stage the raw data, then build dimensions and facts in SQLite."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from core.validators import SCHEMAS

from .config import CATEGORY_GROUPS, DEFAULT_CATEGORY_GROUP, PipelineConfig
from .extract import ExtractedDataset
from .transform import TransformResult

WAREHOUSE_DIR = Path(__file__).resolve().parents[1] / "warehouse"


def date_key(value: str) -> int:
    return int(value.replace("-", ""))


class WarehouseLoader:
    def __init__(self, config: PipelineConfig):
        self.config = config

    # ---- connection and DDL (outside the load transaction) ----
    def connect(self) -> sqlite3.Connection:
        Path(self.config.db_path).parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.config.db_path, isolation_level=None)  # explicit BEGIN/COMMIT
        con.execute("PRAGMA foreign_keys = ON")
        return con

    def prepare(self, con: sqlite3.Connection, datasets) -> None:
        con.executescript((WAREHOUSE_DIR / "schema.sql").read_text())
        for name in datasets:
            cols = ", ".join(f'"{c}" TEXT' for c in SCHEMAS[name]["required"])
            con.execute(f"CREATE TABLE IF NOT EXISTS stg_{name} ({cols}, _run_id TEXT NOT NULL)")

    def create_views(self, con: sqlite3.Connection) -> None:
        con.executescript((WAREHOUSE_DIR / "views.sql").read_text())

    # ---- load (call between BEGIN and COMMIT) ----
    def load(self, con: sqlite3.Connection, run_id: str, extracted: dict[str, ExtractedDataset],
             result: TransformResult) -> str:
        """Returns the as-of date used for aging calculations."""
        clean = result.clean
        self._load_staging(con, run_id, extracted)
        self._load_dim_date(con, clean)
        self._load_dim_category(con, clean)
        self._load_dim_counterparty(con, clean)
        parties = dict(con.execute("SELECT counterparty_name, counterparty_key FROM dim_counterparty"))
        cats = dict(con.execute("SELECT category_name, category_key FROM dim_category"))
        self._load_fact_transactions(con, run_id, clean["transactions"], parties, cats)
        self._load_invoices(con, "fact_receivables", clean["accounts_receivable"], "customer", parties)
        self._load_invoices(con, "fact_payables", clean["accounts_payable"], "vendor", parties)
        self._load_snapshots(con, clean, parties, cats)
        return self._load_settings(con, clean)

    def _load_staging(self, con, run_id, extracted) -> None:
        for name, ds in extracted.items():
            cols = SCHEMAS[name]["required"]
            con.execute(f"DELETE FROM stg_{name}")
            rows = [tuple(str(r[c]) if c in ds.frame.columns else "" for c in cols) + (run_id,)
                    for _, r in ds.frame.iterrows()]
            marks = ", ".join("?" for _ in range(len(cols) + 1))
            con.executemany(f"INSERT INTO stg_{name} VALUES ({marks})", rows)

    def _load_dim_date(self, con, clean) -> None:
        sources = [("transactions", "date"), ("accounts_receivable", "invoice_date"),
                   ("accounts_receivable", "due_date"), ("accounts_payable", "invoice_date"),
                   ("accounts_payable", "due_date"), ("payroll", "start_date"),
                   ("revenue_assumptions", "month"), ("hiring_plan", "month")]
        values = pd.concat([clean[n][c] for n, c in sources if len(clean[n])], ignore_index=True)
        if values.empty:
            return
        days = pd.date_range(values.min(), values.max(), freq="D")
        rows = [(int(d.strftime("%Y%m%d")), d.strftime("%Y-%m-%d"), d.year, (d.month - 1) // 3 + 1,
                 d.month, d.strftime("%B"), d.strftime("%Y-%m"), d.day, d.weekday(),
                 d.strftime("%A"), int(d.weekday() >= 5)) for d in days]
        con.executemany("INSERT OR IGNORE INTO dim_date VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)

    def _load_dim_category(self, con, clean) -> None:
        names = sorted(set(clean["transactions"]["category"]) | set(clean["recurring_expenses"]["category"]))
        con.executemany(
            "INSERT OR IGNORE INTO dim_category (category_name, category_group) VALUES (?, ?)",
            [(n, CATEGORY_GROUPS.get(n, DEFAULT_CATEGORY_GROUP)) for n in names])

    def _load_dim_counterparty(self, con, clean) -> None:
        t = clean["transactions"]
        customers = set(clean["accounts_receivable"]["customer"]) | set(t.loc[t["type"] == "inflow", "vendor"])
        vendors = (set(t.loc[t["type"] == "outflow", "vendor"]) | set(clean["accounts_payable"]["vendor"])
                   | set(clean["recurring_expenses"]["vendor"]))
        for kind, names in (("customer", customers), ("vendor", vendors)):  # first role wins
            con.executemany(
                "INSERT OR IGNORE INTO dim_counterparty (counterparty_name, counterparty_type) VALUES (?, ?)",
                [(n, kind) for n in sorted(names)])

    def _load_fact_transactions(self, con, run_id, t, parties, cats) -> None:
        """Incremental, idempotent: a known row_hash is only marked as seen again."""
        rows = [(r.row_hash, date_key(r.date), parties[r.vendor], cats[r.category], r.type,
                 float(r.amount), float(r.amount) if r.type == "inflow" else -float(r.amount), run_id, run_id)
                for r in t.itertuples(index=False)]
        con.executemany(
            """INSERT INTO fact_transactions
                   (row_hash, date_key, counterparty_key, category_key, direction, amount, signed_amount,
                    first_run_id, last_run_id)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(row_hash) DO UPDATE SET last_run_id = excluded.last_run_id""", rows)

    def _load_invoices(self, con, table, df, party_col, parties) -> None:
        con.execute(f"DELETE FROM {table}")
        con.executemany(
            f"INSERT INTO {table} (invoice_date_key, due_date_key, counterparty_key, amount, status) VALUES (?,?,?,?,?)",
            [(date_key(r.invoice_date), date_key(r.due_date), parties[getattr(r, party_col)], float(r.amount), r.status)
             for r in df.itertuples(index=False)])

    def _load_snapshots(self, con, clean, parties, cats) -> None:
        for table in ("fact_recurring_expenses", "fact_payroll", "fact_revenue_plan", "fact_hiring_plan"):
            con.execute(f"DELETE FROM {table}")
        con.executemany(
            "INSERT INTO fact_recurring_expenses VALUES (?,?,?)",
            [(parties[r.vendor], cats[r.category], float(r.monthly_amount))
             for r in clean["recurring_expenses"].itertuples(index=False)])
        con.executemany(
            "INSERT INTO fact_payroll VALUES (?,?,?,?)",
            [(r.employee_id, r.role, date_key(r.start_date), float(r.monthly_salary))
             for r in clean["payroll"].itertuples(index=False)])
        con.executemany(
            "INSERT INTO fact_revenue_plan VALUES (?,?)",
            [(date_key(r.month), float(r.expected_revenue)) for r in clean["revenue_assumptions"].itertuples(index=False)])
        con.executemany(
            "INSERT INTO fact_hiring_plan (month_date_key, role, headcount, monthly_salary, monthly_cost) VALUES (?,?,?,?,?)",
            [(date_key(r.month), r.role, int(r.count), float(r.monthly_salary), int(r.count) * float(r.monthly_salary))
             for r in clean["hiring_plan"].itertuples(index=False)])

    def _load_settings(self, con, clean) -> str:
        t = clean["transactions"]
        as_of = self.config.as_of_date or (t["date"].max() if len(t) else pd.Timestamp.today().strftime("%Y-%m-%d"))
        con.executemany(
            "INSERT INTO ref_settings VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            [("starting_cash", str(self.config.starting_cash)), ("as_of_date", as_of)])
        return as_of
