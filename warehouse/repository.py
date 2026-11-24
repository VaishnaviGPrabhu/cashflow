"""Model layer: read-only access to the warehouse.

The API (controller) and the web page (view) never write SQL; they call these
functions, which run parameterised queries against the reporting views.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from pipeline.config import PipelineConfig


class WarehouseNotReady(Exception):
    """The warehouse file does not exist yet (the pipeline has not been run)."""


def get_db_path() -> Path:
    return Path(PipelineConfig.from_env().db_path)  # CASHFLOW_DB is read at call time


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else get_db_path()
    if not path.exists():
        raise WarehouseNotReady(f"Warehouse not found at {path}. Run: python -m pipeline.run_pipeline")
    con = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)  # read-only
    con.row_factory = sqlite3.Row
    return con


def _rows(sql: str, params: tuple = (), db_path: Path | None = None) -> list[dict]:
    con = connect(db_path)
    try:
        return [dict(r) for r in con.execute(sql, params).fetchall()]
    except sqlite3.OperationalError as exc:  # e.g. views missing because no run has succeeded yet
        raise WarehouseNotReady(f"Warehouse is not ready: {exc}") from exc
    finally:
        con.close()


def monthly_cashflow(db_path: Path | None = None) -> list[dict]:
    return _rows("SELECT * FROM vw_monthly_cashflow ORDER BY year_month", db_path=db_path)


def vendor_spend(limit: int = 10, db_path: Path | None = None) -> list[dict]:
    return _rows("SELECT * FROM vw_vendor_spend ORDER BY spend_rank LIMIT ?", (int(limit),), db_path)


def runway(db_path: Path | None = None) -> dict:
    rows = _rows("SELECT * FROM vw_runway", db_path=db_path)
    return rows[0] if rows else {}


def receivables_aging(db_path: Path | None = None) -> list[dict]:
    return _rows("SELECT * FROM vw_receivables_aging ORDER BY days_past_due DESC", db_path=db_path)


def payables_due(db_path: Path | None = None) -> list[dict]:
    return _rows("SELECT * FROM vw_payables_due ORDER BY days_until_due", db_path=db_path)


def last_run(db_path: Path | None = None) -> dict:
    rows = _rows("SELECT * FROM etl_run_log ORDER BY started_at DESC LIMIT 1", db_path=db_path)
    return rows[0] if rows else {}


def latest_quality_results(db_path: Path | None = None) -> list[dict]:
    return _rows(
        """SELECT check_name, dataset, severity, passed, details FROM dq_results
           WHERE run_id = (SELECT run_id FROM etl_run_log WHERE status = 'SUCCESS'
                           ORDER BY started_at DESC LIMIT 1)
           ORDER BY passed, severity, dataset""", db_path=db_path)
