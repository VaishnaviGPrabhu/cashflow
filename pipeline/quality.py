"""Data-quality checks. Each check returns a DQResult that is stored in `dq_results`."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .extract import ExtractedDataset
from .transform import TransformResult


@dataclass
class DQResult:
    check: str
    dataset: str
    severity: str  # HIGH blocks the load; MEDIUM / LOW are reported only
    passed: bool
    details: str = ""


class DataQualityChecker:
    def pre_load(self, extracted: dict[str, ExtractedDataset], result: TransformResult) -> list[DQResult]:
        """Checks on the data before anything is written to the warehouse."""
        out: list[DQResult] = []
        for name, ds in extracted.items():
            out.append(DQResult("source_not_empty", name, "HIGH", ds.row_count > 0, f"{ds.row_count} rows read"))
            rejected = len(result.rejects_for(name))
            out.append(DQResult("rows_rejected", name, "MEDIUM", rejected == 0, f"{rejected} rejected"))
        repeats = int(result.clean["transactions"]["is_repeat"].sum())
        out.append(DQResult("repeated_transaction_rows", "transactions", "LOW", repeats == 0,
                            f"{repeats} row(s) identical to an earlier row"))
        for name in ("accounts_receivable", "accounts_payable"):
            df = result.clean[name]
            bad = int((df["due_date"] < df["invoice_date"]).sum()) if len(df) else 0
            out.append(DQResult("due_date_not_before_invoice_date", name, "MEDIUM", bad == 0, f"{bad} invoice(s)"))
        return out

    def post_load(self, con: sqlite3.Connection, extracted: dict[str, ExtractedDataset],
                  result: TransformResult, run_id: str) -> list[DQResult]:
        """Reconciliation checks run inside the load transaction, before COMMIT."""
        out: list[DQResult] = []
        for name in extracted:
            staged = con.execute(f"SELECT COUNT(*) FROM stg_{name}").fetchone()[0]
            accounted = len(result.clean[name]) + len(result.rejects_for(name))
            out.append(DQResult("staging_row_reconciliation", name, "HIGH", staged == accounted,
                                f"staged={staged}, clean+rejected={accounted}"))
        clean = result.clean["transactions"]
        for direction in ("inflow", "outflow"):
            expected = round(float(clean.loc[clean["type"] == direction, "amount"].sum()), 2)
            actual = con.execute(
                "SELECT COALESCE(SUM(amount),0) FROM fact_transactions WHERE direction=? AND last_run_id=?",
                (direction, run_id)).fetchone()[0]
            out.append(DQResult(f"fact_amount_reconciliation_{direction}", "fact_transactions", "HIGH",
                                abs(round(actual, 2) - expected) < 0.01, f"source={expected}, warehouse={round(actual, 2)}"))
        orphans = con.execute("PRAGMA foreign_key_check").fetchall()
        out.append(DQResult("foreign_key_integrity", "warehouse", "HIGH", not orphans, f"{len(orphans)} orphan row(s)"))
        return out

    @staticmethod
    def blocking(results: list[DQResult]) -> list[DQResult]:
        return [r for r in results if r.severity == "HIGH" and not r.passed]
